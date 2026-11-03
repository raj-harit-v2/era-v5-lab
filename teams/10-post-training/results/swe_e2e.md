# One SWE task, end to end

Run on this machine with Docker (`python:3.12-slim`). All task files live in `teams/10-post-training/swe-task/` (`calc.py`, `test_calc.py`, `run_e2e.py`, `Dockerfile`).

## End-to-end flow

1. **Seed failing state (`teams/10-post-training/swe-task/calc.py`):** `add(a, b)` returns `a + b + 1`.
2. **Run test in Docker (`python -m unittest test_calc.py`):** `test_add` asserts `add(2, 3) == 5`, fails with `AssertionError: 6 != 5`, and exits `1`.
3. **Apply patch (`calc.py`):** tool call replaces `return a + b + 1` with `return a + b`.
4. **Re-run test in Docker:** `test_add` prints `OK` and exits `0`.
5. **Render & parse trajectory (`teams/10-post-training/chat-format/render.py`):** the 7-turn agent trajectory (`system` -> `user` -> `assistant read_file` -> `tool` -> `assistant apply_patch` -> `tool` -> `assistant`) is rendered with effort budget `4k` and verified by `parse()`.

## Commands (from `era-v5-lab/`)

### 1. Standalone image build & run (fail -> fix -> pass)

```text
docker build -t g10-swe-add:fail teams/10-post-training/swe-task
docker run --rm g10-swe-add:fail
```

```text
FAIL: test_add (test_calc.AddTests.test_add)
AssertionError: 6 != 5
Ran 1 test in 0.000s
FAILED (failures=1)
```

Exit code `1`. After patching `calc.py` to `return a + b`:

```text
docker build -t g10-swe-add:pass teams/10-post-training/swe-task
docker run --rm g10-swe-add:pass
```

```text
Ran 1 test in 0.000s
OK
```

Exit code `0`.

### 2. Full end-to-end loop in Docker with `render.py`

Standard execution:
```text
docker run --rm \
  -v "$PWD/teams/10-post-training:/app" \
  -w /app/swe-task python:3.12-slim python run_e2e.py
```

Security-hardened air-gapped execution (frontier sandboxing with network isolation and dropped capabilities):
```text
docker run --rm \
  --network none \
  --cap-drop=ALL \
  --security-opt=no-new-privileges:true \
  -v "$PWD/teams/10-post-training:/app" \
  -w /app/swe-task python:3.12-slim python run_e2e.py
```

```text
[step 1] initial test exit=1
FAIL: test_add (test_calc.AddTests.test_add)
AssertionError: 6 != 5
FAILED (failures=1)
[step 2] post-patch test exit=0
Ran 1 test in 0.000s
OK
[step 3] chat_format_v0 render/parse verified: effort=4k turns=7
```

## Security & Scalability Roadmap for Weeks 2–4

- **Air-Gapped Sandboxing (`--network none`):** Guaranteed offline execution prevents remote code exfiltration, unauthorized network requests, or untrusted package fetching during agent evaluation.
- **Privilege Separation:** Non-root execution with kernel capability dropping (`--cap-drop=ALL`) mitigates container breakout and host filesystem tampering.
- **Benchmark Transition:** Scaling from toy test cases (`calc.py`) to repository-level unified diffs (`git apply`) across multi-file repositories for SWE-bench environments.
