# Pull any base image that includes python3
FROM python:3.10

# install the toolbox runner tools
RUN pip install toolbox-runner


# Do anything you need to install tool dependencies here
RUN echo "Replace this line with a tool"

# create the tool input structure
RUN mkdir /in
COPY ./in /in
RUN mkdir /out
RUN mkdir /src
COPY ./src /src

WORKDIR /src
CMD ["python", "run.py"]