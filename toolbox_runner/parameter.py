"""
Use these tools inside the docker container to read and
parse the tool configuration and the parameters.
"""
import os
import json
from yaml import load, Loader


CONF_FILE = '/src/tool.yml'
PARAM_FILE = '/in/tool.json'

def get_env() -> dict:
    return {
        'conf_file': os.environ.get('CONF_FILE', CONF_FILE),
        'param_file': os.environ.get('PARAM_FILE', PARAM_FILE)
    }


def read_config() -> dict:
    # get the config file
    with open(get_env()['conf_file'], 'r') as f:
        return load(f.read(), Loader=Loader)


def _parse_param(key: str, val: str, param_config: dict):
    # switch the type
    c = param_config[key]

    # handle arrays
    if 'array' in c and c['array'] is True:
        return val
    
    t = c['type'].strip()
    if t == 'integer':
        return int(val)
    elif t == 'float':
        return float(val)
    elif t == 'enum' or t == 'string':
        # here we could check the value
        return val.strip()
    else:
        return val


def parse_parameter() -> dict:
    # load the parameter file
    with open(get_env()['param_file']) as f:
        p = json.load(f)

    # load the config
    config = read_config()

    # load only the first section
    # TODO: later, this should work on more than one tool
    section = os.environ.get('TOOL_RUN', list(p.keys())[0])

    # find parameters in config
    param_conf = config['tools'][section]['parameters']

    # container for parsed arguments
    kwargs = {}
    
    # parse all parameter
    for key, value in p[section].items():
        kwargs[key] = _parse_param(key, value, param_conf)

    return kwargs
