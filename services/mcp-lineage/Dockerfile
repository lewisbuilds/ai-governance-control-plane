#### Multi-stage build with requirements.txt install and slim runtime (offline wheelhouse supported)

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Optional proxy/mirror for pip (set via --build-arg)
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

WORKDIR /app
COPY ./services/mcp-lineage /app/services/mcp-lineage
COPY ./wheelhouse* /wheelhouse/

RUN set -eux; \
    if [ -d "/wheelhouse" ] && [ "$(ls -A /wheelhouse)" ]; then \
        python -m venv /app/services/mcp-lineage/.venv; \
        . /app/services/mcp-lineage/.venv/bin/activate; \
        PIP_NO_INDEX=1 PIP_FIND_LINKS=/wheelhouse pip install --no-cache-dir -r /app/services/mcp-lineage/requirements.txt; \
    else \
        python -m venv /app/services/mcp-lineage/.venv; \
        . /app/services/mcp-lineage/.venv/bin/activate; \
        pip install --no-cache-dir -r /app/services/mcp-lineage/requirements.txt; \
    fi

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/services/mcp-lineage/.venv/bin:$PATH"

RUN adduser --disabled-password --gecos "" app
WORKDIR /app/services/mcp-lineage
COPY --from=builder /app/services/mcp-lineage /app/services/mcp-lineage
USER app
EXPOSE 8000
CMD ["uvicorn", "lineage_app:app", "--host", "0.0.0.0", "--port", "8000"]
