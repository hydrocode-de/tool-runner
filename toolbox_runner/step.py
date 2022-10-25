from typing import List
import tarfile

class Step:
    def __init__(self, path: str):
        # set path
        self.path = path

        # some object attributes
        self._members = []
        self._inputs = []
        self._outputs = []
        self._metadata = []

    def _load_members(self):
        with tarfile.open(self.path, mode='r:*') as tar:
            for f in tar:
                self._members.append(f.name)
                if f.name.startswith('./in/'):
                    self._inputs.append(f.name)
                elif f.name.startswith('./out/'):
                    self._outputs.append(f.name)
                else:
                    self._metadata.append(f.name)

    @property
    def members(self) -> List[str]:
        return self._members
    
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
    def log(self):
        """
        TODO: here, we might want to change the structure of the TAR
        """
        log = self.get_file('./out/STDOUT.log').decode()
        return log
    

    def get_file(self, path: str) -> bytes:
        """
        Extract the requested file from the archive and return the content.
        You may need to decode the returned content bytes.
        """
        with tarfile.open(self.path, mode='r:*') as tar:
            return tar.extractfile(path).read()

    def __str__(self):
        return self.path

    def __repr__(self):
        return self.__str__()
