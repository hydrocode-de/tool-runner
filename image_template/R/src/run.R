# load the parameters parser
source('get_parameters.R')

# get the call parameters for the tool
params <- get_parameters()

# check which tool to run
toolname <- Sys.getenv('TOOL_RUN')
if (toolname == '') {
    toolname <- 'foobar'
}

# Switch for the different tools available in this package
if (toolname == 'foobar') {

} 

# in any other case, the tool was invalid or not configured
else {

}