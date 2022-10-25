import os
from datetime import datetime as dt

from toolbox_runner.parameter import parse_parameter

# parse parameters
kwargs = parse_parameter()

# check if a toolname was set in env
toolname = os.environ.get('TOOL_RUN', 'foobar').lower()

# switch the tool
if toolname == 'foobar':
    # RUN the tool here and create the output in /out
    with open('/out/STDOUT.log', 'w') as f:
        f.write('This toolbox does not include any tool. Did you run the template?\n')

# In any other case, it was not clear which tool to run
else:
    with open('/out/error.log', 'w') as f:
        f.write(f"[{dt.now().isocalendar()}] Either no TOOL_RUN environment variable available, or '{toolname}' is not valid.\n")