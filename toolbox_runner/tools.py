from typing import List

from pydantic import BaseModel
from yaml import load, Loader

from toolbox_runner.docker_client import get_client
from toolbox_runner.models import Tool


class ToolSniffer(BaseModel):
    docker_image: str


    def _get_tool_config(self) -> dict:
        # get a docker client
        client = get_client()

        # check out the yaml in the image
        try:
            raw = client.containers.run(self.docker_image, command='cat /src/tool.yml', remove=True)
        # TODO: change this to the Exception, that occures when the tool.yml is not there
        except Exception:
            return {}

        # parse the yaml
        conf = load(raw, Loader=Loader)

        return conf


    def get_tools(self) -> List[str]:
        conf = self._get_tool_config()

        # the tools are listed as keys in the 'tools' dictionary
        return list(conf['tools'].keys())


    def tool(self, name: str) -> Tool:
        # check out the yaml in the image
        conf = self._get_tool_config()

        # check that the tool is in the keys
        if name not in conf['tools']:
            raise RuntimeError(f'Tool {name} not found in {self.docker_image}')
        
        # build the tool payload
        payload = {**conf['tools'][name], 'docker_image': self.docker_image, 'name': name}
        
        # update the payload for the parameter names
        for k, v in payload['parameters'].items():
            payload['parameters'][k].update({'name': k})
        
        # handle the data
        if 'data' in payload:
            data = payload['data']
            if isinstance(data, list):
                data = {'path': p for p in data}
            else:
                data = {k: {**v, 'path': k} for k, v in data.items()}
            payload['data'] = data

        # use the Tool model to validate everything
        tool = Tool.model_validate(payload)

        return tool


