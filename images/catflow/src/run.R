library(Catflow)

# load the parameters parser
source("get_parameters.R")

# get the call parameters for the tool
params <- get_parameters()

# check if a toolname was set in env
toolname <- tolower(Sys.getenv("TOOL_RUN"))

# default tool make geometry -> future decission for a default tool
if (toolname == "") {
    toolname <- "make_geometry"
}

# Switch for the different tools available in this package
if (toolname == "make_geometry") {
    # add filename to save generated geometry
    params$out.file <- "/out/geometry.geo"

    # run function make.geometry() with params as input parameters
    pdf('/out/geometry.pdf')
    output <- make.geometry(params, plottitle = "Model Geometry") # width, height, resolution
    dev.off()
} else {
    # in any other case, the tool was invalid or not configured
    f <- file("/out/error.log")
    writeLines(paste("[", Sys.time(), "] Either no TOOL_RUN environment variable available, or '", toolname, "' is not valid.\n", sep=""), con=f)
    close(f)
}