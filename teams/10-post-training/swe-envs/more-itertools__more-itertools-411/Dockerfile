# G10 SWE environment image. Repo at the PR base commit, no git history, pinned dependencies.
FROM python:3.8-slim@sha256:1d52838af602b4b5a831beb13a0e4d073280665ea7be7f69ce2382f29c5a613f
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.13.7 \
    && uv venv --quiet --python /usr/local/bin/python3 /venv
ENV VIRTUAL_ENV=/venv PATH=/venv/bin:$PATH
RUN git clone --quiet https://github.com/more-itertools/more-itertools.git /repo && cd /repo \
    && git checkout --quiet d6e773411087fa494991d7a8ad81e6a9ad5ddd56 \
    && git submodule update --init --recursive --quiet \
    && find . -name .git -prune -exec rm -rf {} + \
    && git init --quiet && git add -A \
    && git -c user.name=base -c user.email=base@localhost commit --quiet -m base
WORKDIR /repo
COPY requirements.lock /tmp/requirements.lock
RUN uv pip install --no-deps -r /tmp/requirements.lock \
    && uv pip install --no-deps --exclude-newer 2020-03-29 --exclude-newer-package setuptools=2025-06-01 --exclude-newer-package wheel=2025-06-01 -e .
RUN useradd --create-home runner && chown -R runner /repo
USER runner
