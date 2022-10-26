import os
from datetime import datetime as dt

from pandas_profiling import ProfileReport

from toolbox_runner.parameter import parse_parameter

# parse parameters
kwargs = parse_parameter()

# check if a toolname was set in env
toolname = os.environ.get('TOOL_RUN', 'profile').lower()

# switch the tool
if toolname == 'profile':
    # get the data file 
    df = kwargs['data']  # pd.DataFrame
    profile = ProfileReport(df, title="Dataset Report")

    # generate the output
    profile.to_file('/out/report.html')
    profile.to_json('/out/report.json')


# In any other case, it was not clear which tool to run
else:
    with open('/out/error.log', 'w') as f:
        f.write(f"[{dt.now().isocalendar()}] Either no TOOL_RUN environment variable available, or '{toolname}' is not valid.\n")