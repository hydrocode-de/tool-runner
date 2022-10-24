import os
import json
import tempfile
import shutil
from datetime import datetime as dt

import numpy as np
import pandas as pd


class Tool:
    def __init__(self, name: str, image: str, tag: str, **kwargs):
        self.name = name
        self.image = image 
        self.tag = tag
        self.valid = False
        
        self.title = None
        self.description = None
        self.version = None
        self.parameters = {}

        # build conf
        self._build_config(**kwargs)

    def run(self, host_path: str = None, result_path: str = None, **kwargs):
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
        kwargs : dict, optional
            All possible parameters for the tool. These will be mounted into the
            tool container and toolbox_runner will parse the file inside the
            container. All possible parameters can be accessed by `self.parameters`.
        
        Returns
        -------
        output : str
            If a result path was given, output contains the filename of the created
            archive. Otherwise the captured stdout of the container will returned.
        """
        if not self.valid:
            raise RuntimeError('This tool has no valid configuration.')
        pass
        
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

        # run
        cmd = f"docker run --rm -v {in_dir}:/in -v {out_dir}:/out --env TOOL_RUN={self.name} --env PARAM_FILE=/in/tool.json {self.image}:{self.tag}"
        stream = os.popen(cmd)

        # save the stdout
        stdout = stream.read()
        with open(os.path.join(out_dir, 'STDOUT.log'), 'w') as f:
            f.write(stdout)
        
        # should the results be copied?
        if result_path is not None:
            fname = os.path.join(result_path, f"{int(dt.now().timestamp())}_{self.name}")
            shutil.make_archive(fname, 'gztar', host_path)
            return f"{fname}.tar.gz"
        else:
            return stdout


    def _build_parameter_file(self, path: str, **kwargs) -> str:
        """build the parameter file to run this tools and return the location"""
        params = {}
        
        # check the parameters
        for key, value in kwargs.items():
            # TODO: here we can add all kinds of parameter handling (ie. save files)
            if isinstance(value, np.ndarray):
                # check if this parameter requires only a string
                if self.parameters[key]['type'] == 'file':
                    # save the params
                    fname = f"{key}.dat"
                    np.savetxt(os.path.join(path, fname), value)
                    value = f"/in/{fname}"
                else:
                    value = value.tolist()
            elif isinstance(value, pd.DataFrame):
                if self.parameters[key]['type'] == 'file':
                    # save the params
                    fname = f"{key}.csv"
                    value.to_csv(fname)
                    value = f"/in/{fname}"
                else:
                    value = value.values.tolist()

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
            return f"{self.name}: {self.title}  FROM {self.image}:{self.tag} VERSION: {self.version}"
        else:
            return f"INVALID definition FROM {self.image}:{self.tag}"
    
    def __repr__(self):
        return self.__str__()
