# One Go SWE task, end to end

Run on a local machine with Docker (`golang:1.23-alpine`, go1.23.12, digest `sha256:383395b794dffa5b53012a212365d40c8e37109a626ca30d6151c8348d380b5f`). Task files are in `teams/10-post-training/swe-task-go/` (`go.mod`, `stats.go`, `stats_test.go`, `Dockerfile`, `run_e2e_go.py`). It follows the pattern of `results/swe_e2e.md`, with Go in place of Python.

## End-to-end flow

1. **Seed failing state (`stats.go`):** `Sum` loops from index 1, so it skips the first element.
2. **Run the test in Docker (`go test ./...`):** `TestSum` fails for `[7]` (got 0) and `[1 2 3]` (got 5); exit `1`.
3. **Apply the patch:** the tool call replaces `for i := 1; i < len(nums); i++ {` with `for i := 0; i < len(nums); i++ {`.
4. **Re-run in Docker:** `go test ./...` passes, `go vet ./...` is clean; exit `0`.
5. **Render and parse the trajectory (`chat-format/render.py`):** the 7-turn agent trajectory is rendered at effort `4k` and `parse()` returns the same messages.
6. **Go edge cases:** tabs, CRLF and the channel operator `<-` survive the round trip; a literal `<|im_start|>` or `<think>` inside a Go string is rejected.

## Command (from the repository root)

```text
python teams/10-post-training/swe-task-go/run_e2e_go.py
```

The runner copies the task to a temp directory and runs each `go` command with `docker run --rm --network none --cap-drop=ALL --security-opt=no-new-privileges:true --user <uid>:<gid>`. The repository files are never edited. Set `G10_GO_IMAGE` to use another Go image.

## Output

```text
[step 1] initial test exit=1
--- FAIL: TestSum (0.00s)
    stats_test.go:17: one: Sum([7]) = 0, want 7
    stats_test.go:17: many: Sum([1 2 3]) = 5, want 6
FAIL
FAIL	example.com/g10/stats	0.003s
FAIL
[step 2] post-patch test exit=0
ok  	example.com/g10/stats	0.003s
[step 3] go vet exit=0
[step 4] chat_format_v0 render/parse verified: effort=4k turns=7
[step 5] tabs, CRLF and the channel operator <- survive the round trip
[step 6] rejected as expected: s := "<|im_start|>" -> message 0 content contains special token <|im_start|>
[step 6] rejected as expected: s := "<think>" -> message 0 content contains plain-text marker <think>; every chat marker must be one special token
```

## Notes and limits

- The task is a small authored smoke test, not an external SWE-bench result.
- The Go tests run in Docker; `render.py` runs on the host Python. The image must be pulled once (network needed for the pull only; the runs are offline).
- Unit tests that need no Docker are in `tests/test_go_chat_format.py` (tabs, CRLF, tool-call JSON, rejected markers, StarCoder markers as plain text).
- Open point: a real Go file that contains a literal control marker in a string would be rejected by `render.py`; the data step must drop or escape it (see `chat-format/chat_format_v0.md`).
