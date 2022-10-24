# Pull any base image that includes R
FROM r-base:4.2.0

# the parameter parsing function always needs the rjson package
RUN R -e "install.packages('jsonlite')"

# Do anything you need to install tool dependencies here
RUN echo "Replace this line with a tool"

# create the tool input structure
RUN mkdir /in
COPY ./in /in
RUN mkdir /out
RUN mkdir /src
COPY ./src /src

WORKDIR /src
CMD ["Rscript", "run.R"]
