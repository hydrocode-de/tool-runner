# Pull any base image that includes R
FROM r-base:4.2.0

# the parameter parsing function always needs the rjson and yaml packages
RUN R -e "install.packages(c('jsonlite', 'yaml'))"

# install Catflow-R-Package dependencies
RUN R -e "install.packages(c('deSolve', 'RColorBrewer', 'zoo', 'xts'))"

# create the tool input structure
RUN mkdir /in
COPY ./in /in
RUN mkdir /out
RUN mkdir /src
COPY ./src /src

# COPY CATFLOW-R-Package source code
COPY ./src/Catflow-R-Package ./src/Catflow-R-Package

# install Catflow-R-Package from source
RUN R -e "install.packages('/src/Catflow-R-Package', repos = NULL, type = 'source')"

WORKDIR /src
CMD ["Rscript", "run.R"]
