"""
Use these tools inside the docker container to read and
parse the tool configuration and the parameters.
"""
import os
import json
from yaml import load, Loader
import numpy as np
import pandas as pd


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
    if isinstance(val, (list, tuple)):
        return [_parse_param(key, _, param_config) for _ in val]
    
    # get type from tool yaml
    t = c['type'].strip()

    # handle specific types
    if t == 'enum':
        val = val.strip()
        if val not in c['values']:
            raise ValueError(f"The value {val} is not contained in {c['values']}")
        return val
    elif t.lower() in ('datetime', 'date', 'time'):
        # TODO: implement this
        raise NotImplementedError
    elif t == 'file':
        # get the ext and use the corresponding reader
        _, ext = os.path.splitext(val)
        
        # use numpy for matrix files
        if ext.lower() == '.dat':
            val = np.loadtxt(val)
        elif ext.lower() == '.csv':
            val = pd.read_csv(val)
        elif ext.lower() == '.json':
            with open(val, 'r') as f:
                val = json.load(f)
        return val
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
