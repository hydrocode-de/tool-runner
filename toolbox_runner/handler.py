from typing import Optional, Generator, List, Dict
from typing import Any
from pathlib import Path
import json
import warnings
import uuid
from functools import cache
import shutil

import redis
from redis import ConnectionError
from pydantic import Field
from pydantic_settings import BaseSettings

from toolbox_runner.runner import ToolRunner
from toolbox_runner.tools import ToolSniffer
from toolbox_runner.models import ToolJob, ToolJobStatus, ToolResultStatus, Tool

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
    
    def hset(self, key: str, mapping: dict) -> bool:
        return self.set(key, mapping)
    
    def delete(self, key: str):
        if key not in self.store:
            raise KeyError(f"Key '{key}' not found in store")
        
        del self.store[key]
        
        with open(self.__file_location, 'w') as f:
            json.dump(self.store, f, indent=4)


@cache
def get_cached_tool(tool_name: str, docker_image: str) -> Tool | None:
    # use a tool sniffer to get the tool
    sniffer = ToolSniffer(docker_image=docker_image)
    tool = sniffer.tool(name=tool_name)

    return tool

class ToolHandler(BaseSettings):
    redis_host: str = '127.0.0.1'
    redis_port: int = 6379

    tool_map: Dict[str, str] = Field({}, repr=False)

    redis_client: Optional[redis.Redis | FallbackStore] = Field(None, repr=False)
    runner: Optional[ToolRunner] = Field(None, repr=False)

    def _hset(self, key: str, value: dict):
        """
        This wrapper is needed to prevent redis-py from sending NoneType 
        dictionary values.
        """
        self.redis_client.hset(key, mapping={k: v for k, v in value.items() if v is not None})

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
        if self.runner is None:
            self.runner = ToolRunner()

        # load existing registered tools from the Redis store
        if self.redis_client.exists('tool_map'):
            self.tool_map = self.redis_client.hgetall('tool_map')

        return super().model_post_init(__context)
    
    def get_tool(self, tool_name: str) -> Tool | None:
        # get the docker image name of the tool
        docker_image = self.tool_map.get(tool_name, None)
        if docker_image is None:
            return None
        
        # use the function with cache
        tool = get_cached_tool(tool_name, docker_image)

        return tool
    
    def clear_tool_cache(self):
        get_cached_tool.cache_clear()

    def register_tool(self, tool_name: str, docker_image: str) -> bool:
        if tool_name in self.tool_map:
            raise RuntimeError(f"A tool of name {tool_name} is already registered. Currently, tool names have to be unique.")
        
        self.tool_map[tool_name] = docker_image
        self._hset('tool_map', self.tool_map)

        return True

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
            self.register_tool(tool_name, docker_image)
        
        # load the tool specification
        tool = self.get_tool(tool_name)
        
        # create the job
        # this returns the mount points in case they were not pre-defined
        try:
            in_dir, out_dir = self.runner.init_tool(tool=tool, parameter=parameters, data=data, in_dir=in_dir, out_dir=out_dir)
        except Exception as e:
            raise RuntimeError(f"Could not initialize the tool {tool_name} with the given parameters and data. ERROR: {str(e)}")    
 
 
        # crete the tool job entry
        toolJob = ToolJob(
            job_id=str(uuid.uuid4()),
            docker_image=docker_image,
            tool_name=tool_name,
            in_dir=in_dir,
            out_dir=out_dir,
            status=ToolJobStatus.PENDING,
        )

        # set the job in the store
        self._hset(f"tooljob:{toolJob.job_id}", toolJob.model_dump())
        
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
        tool = self.get_tool(job.tool_name)

        # update the job to mark it running
        job.status = ToolJobStatus.RUNNING
        self._hset(f"tooljob:{job_id}", job.model_dump())

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
        self._hset(f"tooljob:{job_id}", job.model_dump())
        
        return job

    def get_job(self, job_id: str) -> ToolJob:
        """
        Return the job metadata for the given job_id
        """
        job_id = f"tooljob:{job_id}" if not job_id.startswith('tooljob:') else job_id
        data = self.redis_client.hgetall(job_id)
        # TODO debug log here
        return ToolJob(**data)

    def delete_job(self, job_id: str, keep_mount_files: bool = False) -> bool:
        """
        Delete a job from the store and optionally remove the mount files
        """
        # check if the mount files should be removed
        if not keep_mount_files:
            # get the job
            job = self.get_job(job_id)

            # remove 
            if job.in_dir is not None:
                shutil.rmtree(job.in_dir, ignore_errors=True)
                shutil.rmtree(job.out_dir, ignore_errors=True)
        
        # delete the metadata itself
        self.redis_client.delete(f"tooljob:{job_id}")
        return True

    def list_jobs(self, ids_only: bool = True) -> List[str] | List[ToolJob]:
        """
        List all keys starting with tooljob:* from the store

        Currently, filtering (ie. for status) is not supported
        """
        # get the list
        scan_list = [job_id.split(':')[-1] for job_id in self.redis_client.scan_iter('tooljob:*')]
        
        # return either a list of ids or the full list
        if ids_only:
            return scan_list
        else:
            return [self.get_job(job_id) for job_id in scan_list]

    

