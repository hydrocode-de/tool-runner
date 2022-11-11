from typing import List, Union, Dict
import os
import glob

from github import Github

from toolbox_runner.image import Image
from toolbox_runner.tool import Tool
from toolbox_runner.step import Step

try:
    stream = os.popen("docker version --format '{{.Server.Version}}'")
    DOCKER = stream.read()
    if DOCKER in ['', '\n']:
        raise Exception
except Exception:
    DOCKER = 'na'


def docker_available() -> bool:
    return DOCKER != 'na'


def require_backend(on_fail='error'):
    if docker_available():
        return True
    else:
        if on_fail == 'error':
            raise RuntimeError("Docker engine is not available.")
        elif on_fail == 'info':
            print("Docker engine is not available.")
        else:
            pass


def list_tools(prefix: Union[str, List[str]] = 'tbr_', as_dict: bool = False) -> Union[List[Tool], Dict[str, Tool]]:
    """List all available tools on this docker instance"""
    require_backend()
    
    stream = os.popen("docker image list")
    raw = stream.read()
    lines = raw.splitlines()

    # get the header
    header = [_.lower() for _ in lines[0].split()]

    # check the prefix data type
    if isinstance(prefix, str):
        prefix = [prefix]

    tools = []
    for line in lines[1:]:
        conf = {h: v for h, v in zip(header, line.split()) if h in ('repository', 'tag', 'image')}

        if any([conf['repository'].startswith(pref) for pref in prefix]):
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
    require_backend(on_fail='info')

    if path.endswith('.tar.gz'):
        return Step(path)
    elif os.path.isdir(path):
        files = glob.glob(os.path.join(path, '*.tar.gz'))
        return [Step(fname) for fname in files]
    else:
        raise AttributeError('Path needs to be a directory containing Step tarballs or a path to a single file.')


def get_remote_image_list(repo='hydrocode-de/tool-runner', list_file='tool-list.txt'):
    """Load all images from remote repository"""
    # connect without authentication
    g = Github()

    # spot the file and download
    tlist: bytes = g.get_repo(repo).get_contents(list_file).decoded_content
    tool_images = [_.decode() for _ in tlist.splitlines()]

    return tool_images


def update_tools():
    """Load the list of available vfw tools and pull the images"""
    image_list = get_remote_image_list()

    # pull all images
    for image in image_list:
        os.system(f"docker pull {image}")
