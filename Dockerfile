FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN apt-get update && apt-get upgrade -y
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

CMD ["bash", "run.sh", "uvicorn"]
