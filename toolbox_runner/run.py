from typing import List, Union, Dict
import os
import glob
from toolbox_runner.image import Image
from toolbox_runner.tool import Tool
from toolbox_runner.step import Step

try:
    stream = os.popen("docker version --format '{{.Server.Version}}'")
    DOCKER = stream.read()
    if DOCKER == '':
        raise Exception
except Exception:
    print('Docker engine is not available')
    DOCKER = 'na'


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


def load_steps(path: str) -> Union[Step, List[Step]]:
    """
    Load a tool processing step saved to a tarball.
    The function can load a single step if the path ends with
    ``.tar.gz``, or will load all tarballs from the directory
    if a path is given.

    Parameters
    ----------
    path : str
        A path to single tarball or a directory of tarballs to
        load either one or all tars.
    
    Returns
    -------
    step : List[Step], Step
        The Step represenstation of the path or directory.
    """
    if path.endswith('.tar.gz'):
        return Step(path)
    elif os.path.isdir(path):
        files = glob.glob(os.path.join(path, '*.tar.gz'))
        return [Step(fname) for fname in files]
    else:
        raise AttributeError('Path needs to be a directory containing Step tarballs or a path to a single file.')
