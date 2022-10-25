library(jsonlite)

get_parameters <- function() {
    # get the parameter file env variable
    PARAM_FILE <- Sys.getenv(x = "PARAM_FILE")
    if (PARAM_FILE == "") {
        PARAM_FILE <- "/in/tool.json"
    }

    # config file

    # error: no config file / no parameter file

    # get the tool name
    TOOL <- tolower(Sys.getenv(x = "TOOL_RUN"))

    # parse the json
    params <- read_json(path = PARAM_FILE)

    # parse parameters
    #Endungen: .mat, .csv

    return(params)
}