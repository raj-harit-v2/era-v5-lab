# Go SWE task

One Go task end to end: `stats.go` with a seeded bug (`Sum` skips the first element), tests in `stats_test.go`, run in Docker (`Dockerfile`, `go.mod`) by `run_e2e_go.py`, with the trajectory rendered by `chat-format/render.py`. Run it from the repository root. Results: `results/go_swe_e2e.md`. Checks: `tests/test_go_chat_format.py`.

## Gate

Week 1 extension of the single-task SWE demonstration in `../swe-task/`, for Go. It is not an RL environment; the Go environments built from real PRs are in `../swe-envs/`.

## What has been measured

`results/go_swe_e2e.md` records one Docker run: the test fails before the patch (exit 1), the test and `go vet` are clean after it (exit 0), the 7-turn trajectory renders at effort `4k` and parses back to the same messages, and tabs, CRLF and `<-` survive the round trip. Run-time details are in that report.

## What has not been measured

- No model has attempted the task, and no score is reported.
- The run has not been repeated for this README.
- Go tests in `../tests/test_go_chat_format.py` have not been run for this README.

## Reports

- [../results/go_swe_e2e.md](../results/go_swe_e2e.md)
