# CAD to G-code Platform - Development Dockerfile
# Multi-stage build for small production image

FROM python:3.11-slim-bookworm AS base

# Use Chinese mirrors for faster builds
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.7.0 \
    CAD2GCODE_HOME=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only dependency files first (for better caching)
COPY pyproject.toml .
COPY README.md .

# Install Python dependencies (using Chinese mirror for speed)
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
    fastapi>=0.104.0 \
    "uvicorn[standard]>=0.24.0" \
    pydantic>=2.5.0 \
    pyyaml>=6.0 \
    numpy>=1.24.0 \
    Pillow>=10.0.0 \
    requests>=2.31.0 \
    aiohttp>=3.9.0 \
    python-multipart>=0.0.6 \
    jinja2>=3.1.2 \
    ezdxf>=1.1.0 \
    PyJWT>=2.8.0 \
    bcrypt>=4.0.0 \
    ;

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/
COPY tests/ ./tests/

# Create necessary directories
RUN mkdir -p /app/logs /app/output /app/.cache/models /app/data/samples \
    && chmod -R 777 /app/logs /app/output /app/.cache

# Install the package in development mode
RUN pip install -e . -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# Default command
CMD ["uvicorn", "src.web.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Development stage with additional tools
FROM base AS development

# Install additional dev tools (mirrors already configured from base stage)
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    htop \
    tcpdump \
    && rm -rf /var/lib/apt/lists/*

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Volume mounts for development
VOLUME ["/app/logs", "/app/output", "/app/data/samples"]

# Default user (non-root for security)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

WORKDIR /app
