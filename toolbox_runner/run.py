from typing import List, Union, Dict
import os
import glob

from github import Github
import docker 
from yaml import load, Loader

from toolbox_runner.tool import Tool
from toolbox_runner.step import Step
from toolbox_runner._docker import docker_available, client

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
    
    # load all images
    images = client.images.list()

    # container for tools
    tools = []
    for image in images:
        # get the first repo and tag combination
        repo, tag = image.tags[0].split(':')
        
        # check if this is a Tool image
        if any([repo.startswith(pref) for pref in prefix]):
            # run a container to load the yaml
            raw = client.containers.run(f"{repo}:{tag}", command='cat /src/tool.yml', remove=True)
            conf = load(raw, Loader=Loader)

            # load the tools
            for tool_name, tool_conf in conf['tools'].items():
                tools.append(Tool(tool_name, repo, tag, image.short_id[7:], **tool_conf))
    
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
