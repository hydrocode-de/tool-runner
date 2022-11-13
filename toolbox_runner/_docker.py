import os
import docker

try:
    # check available
    # TODO change to docker SDK at some point
    stream = os.popen("docker version --format '{{.Server.Version}}'")
    DOCKER = stream.read()
    if DOCKER in ['', '\n']:
        raise Exception
    
    # open client
    client = docker.from_env()
except Exception:
    DOCKER = 'na'


def docker_available() -> bool:
    return DOCKER != 'na'
