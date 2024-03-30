FROM python:3.12.2

# create the main directory
RUN mkdir /app
COPY ./toolbox_runner /app/toolbox_runner
COPY ./frontend /app/frontend
COPY ./setup.py /app/setup.py
COPY ./requirements.txt /app/requirements.txt
COPY ./README.md /app/README.md
COPY ./LICENSE /app/LICENSE
COPY ./MANIFEST.in /app/MANIFEST.in

# install dependencies
RUN pip install --upgrade pip && \
    cd /app && \
    pip install -e .


# install nodejs
RUN apt update && apt upgrade -y && \
    apt install nodejs npm -y 

# compile the nodejs application
WORKDIR /app/frontend
RUN npm install && npm run build

WORKDIR /app
CMD ["python", "/app/toolbox_runner/server.py"]
