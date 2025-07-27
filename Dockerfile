FROM python:3.11.11-alpine

WORKDIR /app

COPY ./src .

COPY ./requirements.txt . 

RUN apk update --no-cache && \ 
    apk add --no-cache tzdata && \ 
    apk add --no-cache ca-certificates && \
    apk add --no-cache ffmpeg

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

ENV TZ="Europe/Moscow"

ENTRYPOINT [ "python", "main.py" ]