FROM python:3.8-slim-buster

WORKDIR /code
COPY . .
RUN apt-get -y update && apt-get -y install git
RUN pip install -r requirements.pip

