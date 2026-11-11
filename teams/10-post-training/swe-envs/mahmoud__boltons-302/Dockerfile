# G10 SWE environment image. Repo at the PR base commit, no git history, pinned dependencies.
FROM python:3.10-slim@sha256:6ff506466f8b1e981719b468cc0023b8ef000b983cdec0eafe119d01f379e31d
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.13.7 \
    && uv venv --quiet --python /usr/local/bin/python3 /venv
ENV VIRTUAL_ENV=/venv PATH=/venv/bin:$PATH
RUN git clone --quiet https://github.com/mahmoud/boltons.git /repo && cd /repo \
    && git checkout --quiet 9420cfeb3b1eb270fad876d002bf92567e619b0c \
    && git submodule update --init --recursive --quiet \
    && find . -name .git -prune -exec rm -rf {} + \
    && git init --quiet && git add -A \
    && git -c user.name=base -c user.email=base@localhost commit --quiet -m base
WORKDIR /repo
COPY requirements.lock /tmp/requirements.lock
RUN uv pip install --no-deps -r /tmp/requirements.lock \
    && uv pip install --no-deps --exclude-newer 2022-12-08 --exclude-newer-package setuptools=2025-06-01 --exclude-newer-package wheel=2025-06-01 -e .
RUN useradd --create-home runner && chown -R runner /repo
USER runner
