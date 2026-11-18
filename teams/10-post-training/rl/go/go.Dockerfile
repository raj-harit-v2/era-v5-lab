# Image for the Go verifier (go_verifier.py --sandbox docker):
#   docker build -f teams/10-post-training/rl/go/go.Dockerfile -t g10-go-rl:1 teams/10-post-training/rl/go
# The standard-library build cache is baked in at /opt/gocache. A cold `go build` of the runner takes about 17 s;
# with this cache the container copies it to a tmpfs and builds in under a second. The cache is a copy per run, so
# a candidate cannot change it for the next one. Pin the base image by digest before real training runs.
FROM golang:1.23-alpine
ENV CGO_ENABLED=0 GOPROXY=off GOFLAGS=-mod=mod GOTOOLCHAIN=local GOCACHE=/opt/gocache
RUN mkdir -p /opt/gocache /warm && cd /warm && printf 'module warm\n\ngo 1.23\n' > go.mod \
 && printf 'package main\nimport (_ "bufio"; _ "bytes"; _ "container/heap"; _ "container/list"; _ "encoding/json"; _ "errors"; _ "fmt"; _ "maps"; _ "math"; _ "math/big"; _ "os"; _ "reflect"; _ "regexp"; _ "slices"; _ "sort"; _ "strconv"; _ "strings"; _ "sync"; _ "time"; _ "unicode"; _ "unicode/utf8")\nfunc main(){}\n' > main.go \
 && go build -o /dev/null . && chmod -R a+rX /opt/gocache && rm -rf /warm
