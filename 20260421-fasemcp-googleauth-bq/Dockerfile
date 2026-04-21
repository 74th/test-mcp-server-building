FROM debian:13-slim

RUN groupadd -g 1000 user && \
    useradd -r -u 1000 -g user user

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_PYTHON_INSTALL_DIR=/var/uv/python
ENV UV_CACHE_DIR=/var/uv/cache

WORKDIR /app

COPY .python-version \
    uv.lock \
    pyproject.toml \
    .

RUN  uv sync --frozen --no-install-project

COPY main.py .

RUN mkdir /home/user && chown 1000:1000 /home/user

USER 1000

ENTRYPOINT [".venv/bin/python", "main.py"]
