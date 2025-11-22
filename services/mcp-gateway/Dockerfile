#### Multi-stage build: installs via requirements.txt; offline wheelhouse fallback supported

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Optional proxy/mirror for pip (set via --build-arg) - passed only to build stage when provided
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

WORKDIR /app

# Copy service sources and optional wheelhouse
COPY ./services/mcp-gateway /app/services/mcp-gateway
COPY ./wheelhouse* /wheelhouse/

# Install dependencies into service-local .venv. Use wheelhouse offline if present; otherwise install from PyPI/mirror.
RUN set -eux; \
    if [ -d "/wheelhouse" ] && [ "$(ls -A /wheelhouse)" ]; then \
        python -m venv /app/services/mcp-gateway/.venv; \
        . /app/services/mcp-gateway/.venv/bin/activate; \
        PIP_NO_INDEX=1 PIP_FIND_LINKS=/wheelhouse pip install --no-cache-dir -r /app/services/mcp-gateway/requirements.txt; \
    else \
        python -m venv /app/services/mcp-gateway/.venv; \
        . /app/services/mcp-gateway/.venv/bin/activate; \
        pip install --no-cache-dir -r /app/services/mcp-gateway/requirements.txt; \
    fi

#### Runtime image
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/services/mcp-gateway/.venv/bin:$PATH"

RUN adduser --disabled-password --gecos "" app
WORKDIR /app/services/mcp-gateway
# Copy service directory including its .venv created in builder
COPY --from=builder /app/services/mcp-gateway /app/services/mcp-gateway
USER app
EXPOSE 8000
CMD ["uvicorn", "gateway_app:app", "--host", "0.0.0.0", "--port", "8000"]
