# G10 SWE environment image. Repo at the PR base commit, no git history, pinned dependencies.
FROM python:3.9-slim@sha256:2d97f6910b16bd338d3060f261f53f144965f755599aab1acda1e13cf1731b1b
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.13.7 \
    && uv venv --quiet --python /usr/local/bin/python3 /venv
ENV VIRTUAL_ENV=/venv PATH=/venv/bin:$PATH
RUN git clone --quiet https://github.com/pallets/click.git /repo && cd /repo \
    && git checkout --quiet da2b658e6185b5ae69abcefe755077336024a5e6 \
    && git submodule update --init --recursive --quiet \
    && find . -name .git -prune -exec rm -rf {} + \
    && git init --quiet && git add -A \
    && git -c user.name=base -c user.email=base@localhost commit --quiet -m base
WORKDIR /repo
COPY requirements.lock /tmp/requirements.lock
RUN uv pip install --no-deps -r /tmp/requirements.lock \
    && uv pip install --no-deps --exclude-newer 2021-07-03 --exclude-newer-package setuptools=2025-06-01 --exclude-newer-package wheel=2025-06-01 -e .
RUN useradd --create-home runner && chown -R runner /repo
USER runner
