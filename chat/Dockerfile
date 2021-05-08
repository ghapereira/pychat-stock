# Instructions from https://fastapi.tiangolo.com/deployment/docker/

FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip &&\
    pip install --no-cache-dir -r requirements.txt

COPY ./app /app
