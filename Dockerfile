# NexRoute Fully Reproducible Simulation & Experiment Environment
# Pinned Base Image: Python 3.12 (Debian Bookworm)
FROM python:3.12-slim-bookworm

# Set Environment Variables for SUMO & Python
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    SUMO_HOME=/usr/share/sumo \
    PATH="/usr/share/sumo/tools:/usr/share/sumo/bin:${PATH}" \
    PYTHONPATH="/usr/share/sumo/tools"

# Install Pinned SUMO (v1.15.0) and system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        sumo \
        sumo-tools \
        procps \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement files first for optimal layer caching
COPY backend/requirements.txt /app/backend/requirements.txt
COPY requirements-dev.txt /app/requirements-dev.txt

# Install runtime and development Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt -r /app/requirements-dev.txt

# Copy complete project codebase
COPY . /app

# Default command runs full test suite
CMD ["pytest"]
