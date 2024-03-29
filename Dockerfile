FROM python:3.8-alpine

WORKDIR /

COPY requirements.txt requirements.txt

RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .
