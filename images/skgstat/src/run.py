import os
import json
from datetime import datetime as dt

import skgstat as skg
import numpy as np
from toolbox_runner.parameter import parse_parameter

# parse parameters
kwargs = parse_parameter()

# check if a toolname was set in env
toolname = os.environ.get('TOOL_RUN', 'variogram').lower()

# switch the tool
if toolname == 'variogram':
    # parse the coordinates and values arguments
    # coords = kwargs['coordinates']
    # if isinstance(coords, str):
    #     # TODO: toolbox runner needs something for this
    #     coords = np.loadtxt(coords)

    # values = kwargs['values']
    # if isinstance(values, str):
    #     values = np.loadtxt(values)
    
    # # build the variogram
    # vario = skg.Variogram(coords, values, **{k: v for k,v in kwargs.items() if k not in ('coordinates', 'values')})
    vario = skg.Variogram(**kwargs)

    # create the output
    with open('/out/result.json', 'w') as f:
        json.dump(vario.describe(), f, indent=4)
    
    # create a interactive figure
    skg.plotting.backend('plotly')
    fig = vario.plot()
    fig.write_html('/out/variogram.html')

    # create a PDF
    skg.plotting.backend('matplotlib')
    fig = vario.plot()
    fig.savefig('/out/variogram.pdf', dpi=200)

else:
    with open('/out/error.log', 'w') as f:
        f.write(f"[{dt.now().isocalendar()}] Either no TOOL_RUN environment variable available, or '{toolname}' is not valid.\n")