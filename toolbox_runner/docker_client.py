from typing import Union
import docker
from docker import DockerClient




def docker_version() -> Union[str, 'False']:
    try:
        # try to instantiate the client
        client = docker.from_env()

        # find the docker engine version
        for component in client.version()['Components']:
            if component['Name'] == 'Engine':
                return component['Version']
    except Exception:
        return False


def get_client() -> DockerClient:
    if docker_version():
        return docker.from_env()
    
    else:
        raise RuntimeError('Docker is not available. Have you started the docker daemon?')
