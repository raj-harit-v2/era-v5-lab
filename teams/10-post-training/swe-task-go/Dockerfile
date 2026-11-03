FROM golang:1.23-alpine
WORKDIR /work
COPY go.mod stats.go stats_test.go ./
CMD ["go", "test", "./..."]
