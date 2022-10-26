from typing import List, Union, Dict
import os
from toolbox_runner.image import Image
from toolbox_runner.tool import Tool

try:
    stream = os.popen("docker version --format '{{.Server.Version}}'")
    DOCKER = stream.read()
    if DOCKER == '':
        raise Exception
except Exception:
    print('Docker engine is not available')
    DOCKER = 'na'

# on startup try to find 
def list_tools(prefix='tbr_', as_dict: bool = False) -> Union[List[Tool], Dict[str, Tool]]:
    """List all available tools on this docker instance"""
    stream = os.popen("docker image list")
    raw = stream.read()
    lines = raw.splitlines()

    # get the header
    header = [_.lower() for _ in lines[0].split()]

    tools = []
    for line in lines[1:]:
        conf = {h: v for h, v in zip(header, line.split()) if h in ('repository', 'tag', 'image')}

        if conf['repository'].startswith(prefix):
            image = Image(**conf)
            image_tools = image.load_tools()
            tools.extend(image_tools)
    
    # return type
    if as_dict:
        return {t.name: t for t in tools}
    else:
        return tools
