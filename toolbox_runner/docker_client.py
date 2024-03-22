import os
import docker
from docker import DockerClient

try:
    # check available
    # TODO change to docker SDK at some point
    stream = os.popen("docker version --format '{{.Server.Version}}'")
    DOCKER = stream.read()

    # if the docker CLI did not return anything, it is considered not available
    if DOCKER in ['', '\n']:
        raise Exception
except Exception:
    DOCKER = 'na'


def docker_available() -> bool:
    return DOCKER != 'na'


def get_client() -> DockerClient:
    if docker_available():
        return docker.from_env()
    
    else:
        raise RuntimeError('Docker is not available. Have you started the docker daemon?')
