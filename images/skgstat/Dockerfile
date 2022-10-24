# base image
ARG PYTHON_VERSION=3.10
FROM python:${PYTHON_VERSION}

# install geostatistical libraries
RUN pip install scikit-gstat gstools plotly


# install the Python toolbox-runner
RUN pip install toolbox-runner==0.1.1

# create the tool input structure
RUN mkdir /in
COPY ./in /in
RUN mkdir /out
RUN mkdir /src
COPY ./src /src

WORKDIR /src
CMD ["python", "run.py"]
