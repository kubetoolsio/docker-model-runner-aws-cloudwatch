FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Robust apt (retries) + minimal deps + cleanup
RUN set -eux; \
  for i in 1 2 3; do \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      build-essential \
      curl \
      awscli \
    && break || { echo "apt failed (attempt $i), retrying in 10s..." >&2; sleep 10; }; \
  done; \
  rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

COPY app ./app
EXPOSE 8001
