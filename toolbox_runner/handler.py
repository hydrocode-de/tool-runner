from typing import Optional, Generator, List, Dict
from enum import StrEnum
from typing import Any
from pathlib import Path
import json
import warnings
import uuid

import redis
from redis import ConnectionError
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from toolbox_runner.runner import ToolRunner
from toolbox_runner.tools import ToolSniffer

class FallbackStore:
    __file_location: str = Path(__file__).parent / 'store.json'

    def __init__(self):
        if not self.__file_location.exists():
            self.store = {}
        else:
            with open(self.__file_location, 'r') as f:
                self.store = json.load(f)

    def exists(self, key: str) -> bool:
        return key in self.store
    
    def get(self, key: str) -> str | int | dict | None:
        return self.store.get(key, None)

    def hgetall(self, key: str) -> dict | None:
        return self.store.get(key, {})
    
    def scan_iter(self, key: str | None = None) -> Generator[str, None, None]:
        for k in self.store.keys():
            if key is not None and not k.startswith(key.strip('*')):
                continue
            yield k

    def set(self, key: str, value: str | int | dict) -> bool:
        # set into the store
        self.store[key] = value

        # write to the file
        with open(self.__file_location, 'w') as f:
            json.dump(self.store, f, indent=4)
        
        return True
    
    def hset(self, key: str, value: dict) -> bool:
        return self.set(key, value)

class ToolJobStatus(StrEnum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'

class ToolResultStatus(StrEnum):
    SUCCESS = 'success'
    WARNING = 'warning'
    ERROR = 'error'

class ToolJob(BaseModel):
    job_id: str
    docker_image: str
    tool_name: str
    in_dir: str
    out_dir: str
    status: ToolJobStatus = ToolJobStatus.PENDING
    result_status: Optional[ToolResultStatus] = None
    error_message: Optional[str] = None
    runtime: Optional[float] = None
    timestamp: Optional[str] = None
    

class ToolHandler(BaseSettings):
    redis_host: str = '127.0.0.1'
    redis_port: int = 6379

    tool_map: Dict[str, str] = Field({}, repr=False)

    redis_client: Optional[redis.Redis | FallbackStore] = Field(None, repr=False)
    runner: Optional[ToolRunner] = Field(None, repr=False)

    def model_post_init(self, __context: Any) -> None:
        # create the redis client
        self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port, db=0, decode_responses=True)

        # try to get the version, set if it does not exist
        try:
            if not self.redis_client.exists('version'):
                self.redis_client.set('version', 1)
        except ConnectionError:
            warnings.warn(f"Could not connect to Redis server, is it running at {self.redis_host}:{self.redis_port}? Using fallback store. Note that this will be a file...")
            self.redis_client = FallbackStore()

        # create an instance of the tool runner
        self.runner = ToolRunner()

        # load existing registered tools from the Redis store
        if self.redis_client.exists('tool_map'):
            self.tool_map = self.redis_client.hgetall('tool_map')

        return super().model_post_init(__context)
    
    def create_job(
        self,
        tool_name: str,
        docker_image: Optional[str] = None,
        parameters: dict = {},
        data: dict = {},
        in_dir: Optional[str] = None,
        out_dir: Optional[str] = None
    ) -> ToolJob:
        """
        Create a new job for running by setting up the ToolRunner and creating a
        ToolJob entry in the Redis database.

        """
        # if the docker image is None, we need a full tool name build like: docker_image::tool_name
        if docker_image is None:
            if '::' in tool_name:
                docker_image, tool_name = tool_name.split('::')
            elif tool_name in self.tool_map:
                docker_image = self.tool_map[tool_name]
            else:
                ValueError(f"Tool of name {tool_name} is not kwown to this Handler. Pass the containing 'docker_image' or prefix the tool name as docker_image::tool_name. The image will be registered for future use.")

        # check if the tool is already registered:
        if tool_name not in self.tool_map:
            self.tool_map[tool_name] = docker_image
            self.redis_client.hset('tool_map', self.tool_map)
        
        # load the tool specification
        sniffer = ToolSniffer(docker_image=docker_image)
        tool = sniffer.tool(name=tool_name)
        
        # create the job
        # this returns the mount points in case they were not pre-defined
        did_error = False
        try:
            in_dir, out_dir = self.runner.init_tool(tool=tool, parameter=parameters, data=data, in_dir=in_dir, out_dir=out_dir)
        except Exception as e:
            did_error = str(e)
            if in_dir is None:
                in_dir = 'UNSET'
            if out_dir is None:
                out_dir = 'UNSET'
            warnings.warn(f"TOOL INIT FAILED: {str(e)}")
            
        finally:
            # crete the tool job entry
            toolJob = ToolJob(
                job_id=str(uuid.uuid4()),
                docker_image=docker_image,
                tool_name=tool_name,
                in_dir=in_dir,
                out_dir=out_dir,
                status=ToolJobStatus.PENDING if not did_error else ToolJobStatus.FAILED,
                error_message=did_error if did_error else None
            )

        # set the job in the store
        self.redis_client.hset(f"tooljob:{toolJob.job_id}", toolJob.model_dump())
        
        # return the job
        return toolJob

    def run_job(self, job_id: str, extra_mounts: List[str] = [], extra_args: dict = {}, extra_env: Dict[str, str] = {}) -> ToolJob:
        """
        Load the job-info from the store and run it using the ToolRunner
        """
        # check for the job_id
        if not self.redis_client.exists(f"tooljob:{job_id}"):
            raise ValueError(f"Job with id {job_id} not found in the store")
        
        # get the job
        job = self.get_job(job_id)

        # use the sniffer to get access to the tool
        sniffer = ToolSniffer(docker_image=job.docker_image)
        tool = sniffer.tool(name=job.tool_name)

        # update the job to mark it running
        job.status = ToolJobStatus.RUNNING
        self.redis_client.hset(f"tooljob:{job_id}", job.model_dump())

        # run the tool
        try:
            metadata = self.runner.run(tool=tool, in_dir=job.in_dir, out_dir=job.out_dir, extra_args=extra_args, extra_mounts=extra_mounts, extra_env=extra_env)
            
            # in any other case mark the job as completed
            job.status = ToolJobStatus.COMPLETED
            job.result_status = ToolResultStatus.SUCCESS
            job.runtime = metadata['runtime']
            job.timestamp = metadata['timestamp']
        except Exception as e:
            job.status = ToolJobStatus.FAILED
            job.error_message = str(e)
            
        # here we can also check the out_dir for an STDERR.log
        err_path = Path(job.out_dir) / 'STDERR.log'
        if err_path.exists():
            error_msg = err_path.read_text()
            if error_msg != '':
                job.error_message = error_msg
                job.result_status = ToolResultStatus.ERROR
                
        # update the job
        self.redis_client.hset(f"tooljob:{job_id}", job.model_dump())
        
        return job

    def get_job(self, job_id: str) -> ToolJob:
        """
        Return the job metadata for the given job_id
        """
        data = self.redis_client.hgetall(f"tooljob:{job_id}")
        # TODO debug log here
        return ToolJob(**data)


    def list_jobs(self, ids_only: bool = True) -> List[str] | List[ToolJob]:
        """
        List all keys starting with tooljob:* from the store

        Currently, filtering (ie. for status) is not supported
        """
        # get the list
        scan_list = [ToolJob(**job) for job in self.redis_client.scan_iter('tooljob:*')]
        
        # return either a list of ids or the full list
        if ids_only:
            return [job.job_id for job in scan_list]
        else:
            return scan_list

    

