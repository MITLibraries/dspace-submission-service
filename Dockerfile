FROM python:3.12-slim AS build

RUN apt-get update && apt-get upgrade -y && apt-get install -y git

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_SYSTEM_PYTHON=1
ENV PYTHONPATH=/app

WORKDIR /app

# Copy project metadata
COPY pyproject.toml uv.lock* ./

# Copy CLI source
COPY submitter ./submitter

# Install package into system python
RUN uv pip install --system .

ENTRYPOINT ["submitter"]