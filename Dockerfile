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

RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.13.3-alpine

WORKDIR /app

RUN apk add --no-cache \
    libffi \
    openssl

COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

COPY src/ .
COPY docker.alembic.ini ./alembic.ini

RUN mkdir -p /home/app/db_data && \
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

RUN addgroup -g 1000 app && \
    adduser -D -u 1000 -G app app && \
    chown -R app:app /app /home/app

USER app
