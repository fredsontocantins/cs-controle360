# syntax=docker/dockerfile:1.6
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps required by openpyxl/pandas/reportlab at runtime are already
# covered by the python base image.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application sources (but not .venv, data or tests — see .dockerignore).
COPY cs_control ./cs_control
COPY cs_web ./cs_web
COPY scripts ./scripts
COPY run-server.sh ./

RUN mkdir -p /app/cs_web/data /app/cs_web/static/uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8000/login || exit 1

CMD ["uvicorn", "cs_web.main:app", "--host", "0.0.0.0", "--port", "8000"]
