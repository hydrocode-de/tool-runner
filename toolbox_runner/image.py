from typing import List
import os
from yaml import load, Loader

from toolbox_runner.tool import Tool

class Image:
    def __init__(self, repository: str, tag: str = None, image: str = None, **kwargs):
        # init parameters
        self.repository = repository
        self.tag = tag if tag is not None else 'latest'
        self.image = image
        self._kwargs = kwargs

        self.tools = []

    def load_tools(self) -> List[Tool]:
        """Run the container to return the content of /src/tool.yml"""
        # run the container to read the config
        if len(self.tools) > 0:
            return self.tools

        cmd = f"docker run --rm {self.repository}:{self.tag} cat /src/tool.yml"
        stream = os.popen(cmd)
        conf = load(stream.read(), Loader=Loader)

        # build tool representations
        tools = []
        for tool_name, tool_conf in conf['tools'].items():
            tools.append(Tool(tool_name, self.repository, self.tag, image=self.image, **tool_conf))
        
        if 'caching' in self._kwargs and not self._kwargs['caching']:
            return tools
        else:
            self.tools = tools
            return self.tools

    def __str__(self):
        return f"<{self.repository}> VERSION: {self.tag}"

    def __repr__(self):
        return self.__str__()
