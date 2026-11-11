# G10 SWE environment image. Repo at the PR base commit, no git history, pinned dependencies.
FROM golang:1.21-bookworm@sha256:c6a5b9308b3f3095e8fde83c8bf4d68bd101fce606c1a0a1394522542509dda9
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --quiet https://github.com/Masterminds/semver.git /repo && cd /repo \
    && git checkout --quiet fa798760a0f6fea2b75487106bf42a919134d049 \
    && git submodule update --init --recursive --quiet \
    && find . -name .git -prune -exec rm -rf {} + \
    && git init --quiet && git add -A \
    && git -c user.name=base -c user.email=base@localhost commit --quiet -m base
WORKDIR /repo
ENV GOFLAGS=-mod=readonly GOTOOLCHAIN=local GOCACHE=/tmp/gocache
RUN if [ -f go.mod ]; then go mod download; else go mod init github.com/Masterminds/semver && go mod tidy; fi
RUN chmod -R a+rwX /go
RUN useradd --create-home runner && chown -R runner /repo
USER runner
