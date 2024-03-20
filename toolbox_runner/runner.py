from typing import TYPE_CHECKING, Optional, Literal, Tuple, Dict, List
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from string import ascii_letters
from random import choice
import shutil
import json
from time import time

from docker.errors import APIError
from pydantic_settings import BaseSettings
from pydantic import Field

if TYPE_CHECKING:
    from toolbox_runner.models import Tool
from toolbox_runner.docker import get_client
from toolbox_runner import __version__

BASE_DIR = (Path(__file__) / 'tool_mounts').parent
# BASE_DIR = Path('~/tool_runner').expanduser()


class ToolRunner(BaseSettings):
    mount_base_dir: str = BASE_DIR
    name_mode: Literal['uuid', 'tool_name', 'random'] = Field('random', description="Defines how the tool_runner will name the mount directories for a tool run.")
    rename_input_files: bool = True

    @property
    def mount_path(self):
        p = Path(self.mount_base_dir)

        # create the path if it does not exist
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)

        return p
    
    def _get_tool_mount_name(self, tool_name: Optional[str] = None) -> str:
        # if the name was already created, return that
        if hasattr(self, '__tool_mount_name'):
            return self.__tool_mount_name
        
        # otherwise create a name
        if self.name_mode == 'uuid':
            self.__tool_mount_name = str(uuid4())
        elif self.name_mode == 'tool_name':
            if tool_name is None:
                raise ValueError("Tool name mode requires a tool object to be passed.")
            self.__tool_mount_name = f"{tool_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        elif self.name_mode == 'random':
            self.__tool_mount_name = ''.join([choice(ascii_letters) for _ in range(12)])
        
        # return the name
        return self.__tool_mount_name

    def create_mount_folders(self, tool_name: str, in_dir: Optional[str] = None, out_dir: Optional[str] = None) -> Tuple[str, str]:
        """
        Create the input and output directories for the tool run.
        By default this will create a random location at the base mount path and create a 
        input and output directory there.
        
        """
        # create the input dir at the correct location
        if in_dir is None:
            in_dir = self.mount_path / self._get_tool_mount_name(tool_name=tool_name) / 'in'
        else:
            in_dir = Path(in_dir)

        # create the output dir at the correct location
        if out_dir is None:
            out_dir = self.mount_path / self._get_tool_mount_name(tool_name=tool_name) / 'out'
        else:
            out_dir = Path(out_dir)

        # create the directories if they do not exist
        in_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        return (str(in_dir), str(out_dir))
    
    def copy_input_data(self, in_dir: str, data_files: Dict[str, str] = {}) -> Dict[str, str]:
        """
        Copies the given list of data_files into the in_dir for the tool
        run. The list should be created using the toolbox_runner.models.Data class,
        so that it was checked for being valid.

        """
        # create the mapping for the files
        copied_files = {}

        # get the input path
        in_path = Path(in_dir)

        # go for each file
        for name, file_name in data_files.items():
            file_path = Path(file_name)
            # figure out the out name
            if self.rename_input_files:
                out_name = in_path / f"{name}{file_path.suffix}"
            else:
                out_name = in_path / file_path.name
            
            # copy the file
            shutil.copy(file_path, out_name)

            # add to the out-mapping
            copied_files[name] = str(out_name)

        # return the mapping
        return copied_files

    def create_input_parameterization(self, tool_name: str, input_parameter: dict, in_dir: str, copied_data: Dict[str, str]) -> str:
        """
        Create the inputs.json in the already created mount location.
        The input parameters have already been validated and the the data files 
        are already copied into the mount dir. This function will copy the input_parameter
        and the configuration of the copied files together and create the actual 
        json parameterization file.

        """
        # create the input path
        in_path = Path(in_dir)

        # create the inputs.json
        inputs_json = in_path / 'inputs.json'

        # replace the data settings with the config of the copied data
        input_parameter[tool_name]['data'] = copied_data

        # write the json
        with open(inputs_json, 'w') as f:
            json.dump(input_parameter, f, indent=4)
        
        return str(inputs_json)
    
    def init_tool(self, tool: 'Tool', parameter: dict, data: Dict[str, str], in_dir: Optional[str] = None, out_dir: Optional[str] = None) -> Tuple[str, str]:
        # first step is to validate given parameter and data
        input_config = tool.input_file(parameter=parameter, data=data)

        # if there were no validation error, build the mount directories
        in_dir, out_dir = self.create_mount_folders(tool_name=tool.name, in_dir=in_dir, out_dir=out_dir)
        
        # copy the input data
        copied_data = self.copy_input_data(in_dir=in_dir, data_files=input_config['data'])

        # inject the new info to the parameterization and create the file
        self.create_input_parameterization(tool_name=tool.name, input_parameter=input_config, in_dir=in_dir, copied_data=copied_data)

        # TODO: we should add something here to indicate in the folder, that the tool has
        # successfully been initialized
        return (in_dir, out_dir)
    
    def run(self, tool: 'Tool', in_dir: str, out_dir: str, extra_mounts: List[str] = [], extra_args: dict = {}, extra_env: Dict[str, str] = {}) -> None:
        """
        Run the tool at the given locations. At first it has to be initialized
        using the init_tool function.
        """
        # build the run args
        run_args = dict(
            image=tool.docker_image,
            volumes=[
                f"{Path(in_dir).resolve()}:/in",
                f"{Path(out_dir).resolve()}:/out",
                *extra_mounts
            ],
            environment=[
                f"TOOL_RUN={tool.name}", 
                *[f"{k.upper()}={v}" for k, v in extra_env.items()]
            ],
            **extra_args
        )

        # get a docker client
        client = get_client()

        # start a timer
        t1 = time()

        try:
            container = client.containers.create(**run_args)

            # TODO: some kind of profiling here?
            container.start()
            container.wait()

            # load the logs from the container
            stdout = container.logs(stdout=True, stderr=False).decode()
            stderr = container.logs(stdout=False, stderr=True).decode()
        
        except APIError as e:
            # Make this better
            print('Could not run the tool container:')
            print(e.explanation)
        finally:
            t2 = time()
        
        # write to the out location
        with open(Path(out_dir) / 'STDOUT.log', 'w') as f:
            f.write(stdout)
        
        if stderr != '':
            with open(Path(out_dir) / 'STDERR.log', 'w') as f:
                f.write(stderr)
        
        # write metadata
        with open(Path(out_dir) / 'RUN_METADATA.json', 'w') as f:
            json.dump({
                'runtime': t2 - t1,
                'toolbox_runner.version': __version__,
                'timestamp': datetime.now().isoformat()
            }, f, indent=4)

        # return the output path
        return out_dir