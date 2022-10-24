library(jsonlite)

get_parameters <- function() {
    # get the parameter file env variable
    PARAM_FILE <- Sys.getenv(x = "PARAM_FILE")
    if (PARAM_FILE == "") {
        PARAM_FILE = "/in/tool.json"
    }

    # get the tool name
    TOOL <- Sys.getenv(x = "TOOL_RUN")

    # parse the json
    dat <- fromJSON(file = PARAM_FILE)

    # return 
}