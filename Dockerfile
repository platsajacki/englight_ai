# Build stage
FROM python:3.13.3-alpine AS builder

WORKDIR /app

RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust

COPY src/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.13.3-alpine

WORKDIR /app

RUN apk add --no-cache \
    libffi \
    openssl

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY src/ .
COPY docker.alembic.ini ./alembic.ini
