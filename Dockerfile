FROM python:3.13.3-slim

WORKDIR /app

COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

RUN mkdir -p /home/app/db_data