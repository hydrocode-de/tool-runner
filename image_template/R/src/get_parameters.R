library(jsonlite)
library(yaml)

get_parameters <- function() {
    # get the parameter file env variable
    PARAM_FILE <- Sys.getenv(x = "PARAM_FILE")
    if (PARAM_FILE == "") {
        PARAM_FILE <- "/in/tool.json"
    }

    # get the config file env variable
    CONF_FILE <- Sys.getenv(x = "CONF_FILE")
    if (CONF_FILE == "") {
        CONF_FILE <- "/src/tool.yml"
    }

    # get the tool name
    TOOL <- tolower(Sys.getenv(x = "TOOL_RUN"))

    # parse the json
    params <- read_json(path = PARAM_FILE, simplifyVector = TRUE)[[TOOL]]
    params_names <- names(params)

    # parse the config yaml, directly access parameters section
    config <- read_yaml("src/tool.yml")
    params_config <- config$tools[[TOOL]]$parameters

    # initiate list to save parsed parameters
    parsed_params <- list()

    # parse parameters
    for (name in params_names) {
        # type of the parameter
        t <- param_config[[name]][["type"]]
        # get the value
        val <- params[[name]]

        # handle specific types
        if (t == "enum") {
            if (!(name %in% params_config[[name]]$values)) {
                stop(paste("The value '", val, "' is not contained in [", paste(params_config[[name]]$values, collapse = " "), "]", sep = ""))
            parsed_params <- c(parsed_params, name = val)
        } else if (t %in% c("datetime", "date", "time")) {
           val <- as.POSIXct(val)
           parsed_params <- c(parsed_params, name = val)
        } else if (t == "file") {
            # get the ext and use the corresponding reader
            ext = tolower(xfun::file_ext())
            if (ext == "mat") {
### extra package benötigt um .mat zu öffnen..
                val <- read.table(val)
            } else if (ext == "csv") {
                val <- read.csv(val)
            }
            parsed_params <- c(parsed_params, name = val)
        } else {
            parsed_params <- c(parsed_params, name = val)
        }
    }

    return(parsed_params)
}

# named list unpacken: do.call(...)!!

# .csv, .mat mit numpy und pandas in /in -> einlesen testen