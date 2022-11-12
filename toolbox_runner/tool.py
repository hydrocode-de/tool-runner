from typing import Union
import os
import json
import tempfile
import shutil
import subprocess
from time import time
from datetime import datetime as dt
from concurrent.futures import ThreadPoolExecutor, Future
from blinker import Signal

import numpy as np
import pandas as pd

from toolbox_runner.step import Step


class Tool:
    """
    Tool execution using toolbox-runner.
    This class represents a tool inside a docker container and can be used to execute the tool
    and create :class:`Step <toolbox_runner.step.Step>` representations.

    The Tool can be run asynchronously. For this, the class has a class attribute called 
    EXECUTOR, which can be any class inheriting from :class:`Executor <concurrent.futures..Executor>`.
    By default, a :class:`ThreadPoolExecutor(max_workers=10) <concurrent.futures..ThreadPoolExecutor>`
    is used, but you can change it at runtime:

    >> from concurrent.futures import ProcessPoolExecutor
    >> Tool.EXECUTOR = ProcessPollExecutor(max_workers=4)

    Make sure, that the arguments passed to the :func:`Tool.run <toolbox_runner.tool.Tool.run>` function
    can be passed to a child process.

    Additionally, the Tool class implements ``blinker`` signals. A default signal is called whenever 
    a :class:`Future <concurrent.futures.Future>` is done. Any subscriber to that signal has to accept
    resulting the :class:`Step <toolbox_runner.step.Step>` or string of Stdout, if no ``result_path`` was passed to run.
    By default there are four signals: 

    * TOOL.INIT 
    * TOOL.FINISHED
    * TOOL.CANCELLED
    * TOOL.ERRORED

    The subscribed function will receive the object that emitted the signal. To easier manage chains of tool calls,
    you can overwirte the the Tool.IDENTIFIER, which will default to the **instance** attribute Tool().name. As
    the singals are implemented as class attributes, you can then use one subscriber to handle a signal of all
    tools (like the ERRORED to cancel a workflow). 
    The second appoach is to overwirte the signal on instance level. Then, the signal will only be called by this 
    specific tool. 

    """
    # define a Executor
    EXECUTOR = ThreadPoolExecutor(max_workers=10)
    
    # define blinker signals
    INIT = Signal()
    FINISHED = Signal()
    CANCELLED = Signal()
    ERRORED = Signal()
    
    def __init__(self, name: str, repository: str, tag: str, image: str = None, **kwargs):
        self.name = name
        self.IDENTIFIER = self.name
        self.repository = repository
        self.image = image
        self.tag = tag
        self.valid = False
        
        self.title = None
        self.description = None
        self.version = None
        self.parameters = {}

        # build conf
        self._build_config(**kwargs)

    @property
    def metadata(self):
        return {
            'name': self.name,
            'repository': self.repository,
            'image': self.image,
            'tag': self.tag
        }

    def _async_wrapper(self, **kwargs) -> Union[Future[Step], Future[str]]:
        """
        The async wrapper submits the run function will all given parameters to the 
        executor initialized in the Tool class.

        The futures can be combined with blinker by adding a callback that will 
        send the specified signal name to indicate the finished execution to 
        a workflow tool.

        """
        # always set the run_async flag to False to prevent concurrent infite loops
        kwargs['run_async'] = False

        # define the signal callback function
        def tool_callback(future: Union[Future[Step], Future[str]]):
            # the tool is done, so check if it has been canceled or errored
            if future.cancelled():
                self.CANCELLED.send({self.IDENTIFIER: 'cancelled'})
            
            # get exections
            exception = future.exception()
            if exception is not None:
                self.ERRORED.send({self.IDENTIFIER: exception})

            # emit the result to all subscribers
            self.FINISHED.send({self.IDENTIFIER: future.result()})

        # add the run function to the executor
        future = Tool.EXECUTOR.submit(self.run, **kwargs)

        # append the callback
        future.add_done_callback(tool_callback)

        # return
        return future

    def run(self, host_path: str = None, result_path: str = None, keep_container: bool = False, run_async: bool = False, **kwargs) -> Union[str, Step, Future]:
        """
        Run the tool as configured. The tool will create a temporary directory to
        create a parameter specification file and mount it into the container.
        The tool running in the container will populate a result directory or 
        print results to Stdout, which will be logged into the out directory.
        As the container terminates, the function will either return a archive of
        input and output files, or return Stdout, depending on how it is called.
        If a host_path is given, the function will not create a temporary dir
        and mount the host system. If a result_path is given, the run environment
        will be archived and copied into the specified path.
        Note: if both are not given, the results will be lost as soon as the container
        terminates and thus only Stdout from the container is printed to the host
        Stdout.

        Parameters
        ----------
        host_path : str, optional
            A host path to mount into the tool container, instead of creating
            a temporary location. If set, this might overwrite files on the host
            system.
        result_path : str, optional
            A path on the host system, where the run environemtn will be archived to.
            This environment contains all input parameter files, all output files and
            a log of Stdout.
        keep_container : bool, optional
            If set to True, the container of the tool run will not be dropped after
            execution. The resulting Step class can be used to package and archive
            the step result along with the container and image as a 100% reproducible
            tool run. Defaults to False.
        run_async : bool
            If set to True, the tool will be run asynchronously in a new Thread using
            Pythons `concurrent.futures` API. The function will immediately return a
            :class:`Future <concurrent.futures.Future>` object which will resolve to
            either a :class:`Step <toolbox_runner.step.Step>` instance or a string.
        kwargs : dict, optional
            All possible parameters for the tool. These will be mounted into the
            tool container and toolbox_runner will parse the file inside the
            container. All possible parameters can be accessed by `self.parameters`.
        
        Returns
        -------
        output : str
            If a result path was given, output contains the filename of the created
            archive. Otherwise the captured stdout of the container will returned.
            If run asynchronously, a :class:`Future <concurrent.futures.Future>` of
            that will be returned immediately.

        """
        # check validity
        if not self.valid:
            raise RuntimeError('This tool has no valid configuration.')
        
        # run asynchronously
        if run_async:
            return self._async_wrapper(host_path=host_path, result_path=result_path, keep_container=keep_container, **kwargs)
        
        # create a temporary directory if needed
        if host_path is None:
            tempDir = tempfile.TemporaryDirectory()
            host_path = tempDir.name
        else:
            tempDir = False
        
        # create in and output structs
        in_dir = os.path.abspath(os.path.join(host_path, 'in'))
        out_dir = os.path.abspath(os.path.join(host_path, 'out'))

        if not os.path.exists(in_dir):
            os.mkdir(in_dir)
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)

        # build the parameter file
        self._build_parameter_file(path=in_dir, **kwargs)

        # switch the keep container settings
        if keep_container:
            rm_set = f"--cidfile {os.path.join(host_path, '.containerid')}"
        else:
            rm_set = "--rm"

        # get the time
        t1 = time()   
        # run
        cmd = f"docker run {rm_set} -v {in_dir}:/in -v {out_dir}:/out --env TOOL_RUN={self.name} --env PARAM_FILE=/in/tool.json {self.repository}:{self.tag}"
        
        # call the container but capture Stdout and Stderr
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        # end time profiling
        t2 = time()

        # save the stdout and stderr
        with open(os.path.join(out_dir, 'STDOUT.log'), 'w') as f:
            f.write(proc.stdout)
        
        with open(os.path.join(out_dir, 'STDERR.log'), 'w') as f:
            f.write(proc.stderr)

        # write the metadata about the container and image
        with open(os.path.join(host_path, 'metadata.json'), 'w') as f:
            json.dump({**self.metadata, 'runtime': t2 - t1}, f, indent=4)
        
        # should the results be copied?
        if result_path is not None:
            fname = os.path.join(result_path, f"{int(dt.now().timestamp())}_{self.name}")
            shutil.make_archive(fname, 'gztar', host_path)
            return Step(path=f"{fname}.tar.gz")
        else:
            return proc.stdout


    def _build_parameter_file(self, path: str, **kwargs) -> str:
        """build the parameter file to run this tools and return the location"""
        params = {}
        
        # check the parameters
        for key, value in kwargs.items():
            # Numpy arrays
            if isinstance(value, np.ndarray):
                # check if this parameter requires only a string
                if self.parameters[key]['type'] == 'file':
                    # TODO: This only works for 1D,2D numpy arrays -> else use a netcdf?
                    # save the params
                    # save 1d and 2d arrays to .dat file
                    if value.ndim <= 2:
                        fname = f"{key}.dat"
                        np.savetxt(os.path.join(path, fname), value)
                        value = f"/in/{fname}"
                    else:
                        raise NotImplementedError("Matrices with dimensionality > 2 will be saved to (custom) text files or netCDF files in the future.")
                else:
                    value = value.tolist()
            
            # data frames
            elif isinstance(value, pd.DataFrame):
                if self.parameters[key]['type'] == 'file':
                    # save the params
                    fname = f"{key}.csv"
                    if value.index.name is not None:
                        value.reset_index(inplace=True)
                    value.to_csv(os.path.join(path, fname), index=None)
                    value = f"/in/{fname}"
                else:
                    value = value.values.tolist()
            
            # JSON
            elif isinstance(value, dict):
                if self.parameters[key]['type'] == 'file':
                    # save the params
                    fname = f"{key}.json"
                    with open(os.path.join(path, fname), 'w') as f:
                        json.dump(value, f, indent=4)
                    value = f"/in/{fname}"
            
            # Copy any file source
            elif isinstance(value, str):
                if self.parameters[key]['type'] == 'file':
                    fname = f"{key}{os.path.splitext(value)[1]}"
                    shutil.copy(value, os.path.join(path, fname))
                    value = f"/in/{fname}"

            # add
            params[key] = value
        
        # build the json structure
        param_conf = {self.name: params}

        fname = os.path.join(path, 'tool.json')
        with open(fname, 'w') as f:
            json.dump(param_conf, f)
        
        return fname

    def _build_config(self, **conf):
        """Check the config"""
        self.title = conf['title']
        self.description = conf['description']
        self.version = conf['version']
        self.parameters = conf['parameters']

        self.valid = True

    def __str__(self):
        if self.valid:
            return f"{self.name}: {self.title}  FROM {self.repository}:{self.tag} VERSION: {self.version}"
        else:
            return f"INVALID definition FROM {self.repository}:{self.tag}"
    
    def __repr__(self):
        return self.__str__()
