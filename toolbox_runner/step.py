from typing import List
import os
from io import StringIO
import tarfile
import json
import shutil
import tempfile
import webbrowser
import time
import glob

import numpy as np
import pandas as pd


class Step:
    def __init__(self, path: str):
        # set path
        self.path = path
        self.fname = os.path.basename(self.path)

        # some object attributes
        self._members = []
        self._inputs = []
        self._outputs = []
        self._metadata = []

        # inspect the tarball
        self._load_members()

    def _load_members(self):
        with tarfile.open(self.path, mode='r:*') as tar:
            for f in tar:
                self._members.append(f.name)
                if f.name.startswith('./in/'):
                    self._inputs.append(os.path.basename(f.name))
                elif f.name.startswith('./out/'):
                    self._outputs.append(os.path.basename(f.name))
                else:
                    self._metadata.append(os.path.basename(f.name))

    @classmethod
    def from_file(cls, path: str) -> 'Step':
        """Instantiate from file path"""
        return Step(path)

    @classmethod
    def from_dir(cls, path: str) -> List['Step']:
        steps = []
        for fname in glob.glob(os.path.join(path, '*.tar.gz')):
            step = Step(fname)
            steps.append(step)
        return steps

    @property
    def members(self) -> List[str]:
        return self._members
    
    @property
    def files(self) -> List[str]:
        return self.members
    
    @property
    def inputs(self) -> List[str]:
        return self._inputs
    
    @property
    def outputs(self) -> List[str]:
        return self._outputs

    @property
    def has_container(self) -> bool:
        """Check if this tool steps container is still present"""
        return '.containerid' in self._metadata

    @property
    def log(self) -> str:
        """
        TODO: here, we might want to change the structure of the TAR
        """
        log = self.get_file('./out/STDOUT.log').decode()
        return log

    @property
    def errors(self) -> str:
        """
        Return the content of the errorlogs
        """
        log = self.get_file('./out/STDERR.log').decode()
        return log

    @property
    def has_errors(self) -> bool:
        return self.errors == ""
    
    @property
    def metadata(self) -> dict:
        """Return the Step metadata as dict"""
        return self.__getitem__('metadata.json')

    def get(self, name: str, default = None):
        """
        Return file content as a Python structure. Currently supported are:
        
        * .dat  -> 1d/2d numpy.array
        * .csv  -> pandas.DataFrame
        * .json -> dict

        The get function will return a default value if the file is not
        found or the file extension is not supported.

        """
        try:
            return self._load_file_to_python(name)
        except Exception:
            # Return the default value
            return default

    def move(self, path: str) -> None:
        """Move the step tarball to a new location on your local system"""
        # always use absolute paths
        path = os.path.abspath(path)
        
        # move tarball to new location
        new_path = shutil.move(self.path, path)

        # update the attributes
        self.path = new_path
        self.fname = os.path.basename(self.path)

    def show(self, name: str, keep_file: bool = False) -> None:
        """
        Show the content of a file in the repository in the webbrowser.
        This will extract the requested file to a temporary location and open
        the webbrowser pointing there. 
        The shown content has to be of type HTML, or there needs to be a registered
        Reducer imported into the Python environment, that can convert the file 
        content to a HTML representation.

        .. note::
            Reducers are not yet implemented into toolbox-runner

        """
        # get the extension of the desired file
        _, ext = os.path.splitext(name)

        # create a temporary file for the HTML file
        tf = tempfile.NamedTemporaryFile(suffix='.html', delete=not keep_file)

        if ext.lower() == '.html':
            # TODO: move this into a default Reducer
            # write the file content
            tf.write(self._load_file_to_python(name=name))

        else:
            raise AttributeError('Currently, only HTML content can be shown directly')

        # the temporary file now contains the HTML preview
        temp_path = f"file://{os.path.abspath(tf.name)}"
        
        # open the web-browser and wait 1 sec to return
        # this is needed to let the browser completely load the file before it is eventually
        # destroyed as this function returns
        webbrowser.open_new_tab(temp_path)
        time.sleep(1)

    def _find_file(self, name: str) -> str:
        """
        Aligns the file name with the path inside the tarball.

        """
        if name in self.files:
            return name
        elif name in self.outputs:
            return f"./out/{name}"
        elif name in self.inputs:
            return f"./in/{name}"
        elif name in self.metadata:
            return f"./{name}"
        else:
            raise FileNotFoundError("The file '{name}' is not contained in this tarball.")

    def extract(self, name: str, path: str):
        """
        Extract the file of given name to the local path.
        """
        # get the path inside the tarball
        tar_path = self._find_file(name)

        # open
        with open(os.path.join(path, self.fname), 'wb') as fb:
                fb.write(self.get_file(tar_path))
    
    def _load_file_to_python(self, name: str):
        # check if it is input or output
        path = self._find_file(name)
        
        # load the content
        content = self.get_file(path)    
        
        # Check the extension
        _, ext = os.path.splitext(path)

        # TODO: implement a Reducer class which can be loaded here from the env. 
        # The class will do the loading, so that the user can intercept this step.
        # Maybe even the tool.yml can provide an import path to 3rd-party Reducers
        if ext.lower() == '.json':
            return json.loads(content.decode())
        elif ext.lower() == '.mat':
            with StringIO(content.decode()) as f:
                return np.loadtxt(f)
        elif ext.lower() == '.csv':
            with StringIO(content.decode()) as f:
                return pd.read_csv(f)
        elif ext.lower() == '.html':
            return content
        else:
            raise AttributeError(f"The extension '{ext}' is currently not supported")

    def get_file(self, path: str) -> bytes:
        """
        Extract the requested file from the archive and return the content.
        You may need to decode the returned content bytes.
        """
        with tarfile.open(self.path, mode='r:*') as tar:
            return tar.extractfile(path).read()

    def __getitem__(self, key: str):
        try:
            return self._load_file_to_python(key)
        except Exception as e:
            raise KeyError(str(e))

    def __str__(self):
        return self.path

    def __repr__(self):
        return self.__str__()
