# JS tasks for RL data v1 (`js_verifier.py`, `tasks/`)

The same design as the Python verifier (`../verifier.py`) and Go verifier (`../go/`), for JavaScript code: a candidate answers with one fenced JS block that defines a function with the name given in `entry_point`. The sandbox gets the candidate's code and the inputs only; the generic runner `_js_runner.js` calls the entry point via Node.js Worker threads and writes the outputs; `js_verifier.py` compares them with the expected values, which never enter the sandbox.

```text
rl/js/
  README.md             this file
  js_verifier.py        reward(), check_task() and the command line
  _js_runner.js         runs inside the sandbox: calls the entry point, writes results.json (inputs only)
  js.Dockerfile         the sandbox image (Node.js 26 Active LTS, Alpine)
  test_js_verifier.py   correct and wrong answer for every task, the cheating cases, the lint
  tasks/<task_id>/      task.json, prompt.md, visible_tests.json, hidden_tests.json, reference.js
```

Needs: Python 3.10 or later with `pytest`, and `node` (26 or later) on `PATH`. `--sandbox docker` also needs Docker (see below).

```bash
python teams/10-post-training/rl/js/js_verifier.py --check-task teams/10-post-training/rl/js/tasks/<task_id> [--sandbox docker]
python teams/10-post-training/rl/js/js_verifier.py --reward teams/10-post-training/rl/js/tasks/<task_id> completion.txt [--sandbox docker]
python -m pytest teams/10-post-training/rl/js/test_js_verifier.py -q -p no:cacheprovider
```

- `completion.txt` is a model answer: any text with a fenced JS block (the last one counts), for example:

  ````text
  Here is my answer.
  ```javascript
  function camelToSnake(s) { ... }
  ```
  ````

  The command prints one JSON line with `reward` (1 only if every visible and hidden test passes), `passed`, `total` and a `reason`. It never prints which hidden test failed.

- To add a task: copy a folder in `tasks/`, change the five files, then run `--check-task` on it with both sandboxes. The lint requires 2 or 3 visible and at least 10 hidden tests, a reference that scores 1, a stub returning `undefined` that scores 0, no hidden call written in the prompt, and a `source` that starts with `original` and names the author. Add a wrong answer for it to `WRONG` in `test_js_verifier.py`.

- A task folder has `reference.js` and `"language": "js"` in `task.json`. A case is `{"args": [...], "expected": <json>}` or `{"args": [...], "raises": "<ExceptionName>"}` where `ExceptionName` is one of `TypeError`, `RangeError`, `SyntaxError`, or `Error`. Exception matching is **subclass-aware**: an error is accepted for `ExceptionName` if `ExceptionName.prototype` appears anywhere in its prototype chain. An instance of `class CustomTypeError extends TypeError {}` therefore satisfies `{"raises": "TypeError"}`. No `kwargs`; args are positional only. `time_limit_s` in `task.json` is the per-case execution timeout in seconds (default `2.0`, permitted range `[0.1, 300]`); the aggregate wall timeout is `n_cases × time_limit_s + STARTUP_S`. Both `reward()` and `check_task()` validate this range before starting candidate execution; invalid values are rejected immediately without running any subprocess.

- **Input isolation**: `_js_runner.js` reads `cases.json` into memory and deletes it from disk immediately, before spawning any Worker. Workers receive only the current case's arguments via `workerData`; they have no path to the full input list. Expected answers never enter the sandbox at all.

- **Authenticated Worker bootstrap**: the Worker code (`WORKER_BOOT`) is a string constant embedded in the runner process memory and passed to each Worker via `eval: true`. It is never written to the work directory, so candidate code cannot replace it by overwriting `/work/runner.js`. Inside each Worker, `parentPort` and `workerData` are nulled before candidate code runs — both `require('worker_threads')` and `process.getBuiltinModule('worker_threads')` return the same cached module object, so a single assignment neutralises every access path candidate code could use. A per-invocation nonce is included in every authentic result message and validated by the main thread; a message without the correct nonce is rejected as malformed, regardless of its shape.

- **Intrinsic capture against prototype mutation**: callable prototype operations — `Function.prototype.call/apply`, `Promise.prototype.then`, and `MessagePort.prototype.postMessage` — are captured as bound functions before `new Function(code)(...)` runs. A bound function is an exotic object whose `[[BoundCall]]` internal method invokes `[[BoundTargetFunction]]` directly, without any prototype chain lookup, so candidate code that replaces these prototype properties after the captures are taken cannot intercept bootstrap operations. Error type prototypes (`TypeError.prototype`, `RangeError.prototype`, `SyntaxError.prototype`) are captured as plain references (not bound functions); they are used only for prototype-chain identity tests via `isPrototypeOf`. Result messages are built with null-prototype object literals (not `Object.assign`) so `Object.assign` replacement has no effect. The `Promise` constructor is captured before candidate code so `globalThis.Promise` replacement cannot affect the execution chain.

- **Exception semantics**: exception classification uses `util.types.isNativeError` (V8's `IsNativeError()`) as a first gate, followed by `isPrototypeOf` checks against captured prototype references. `isNativeError` accepts genuine native Error objects — including instances of user-defined subclasses (`class CustomTypeError extends TypeError {}`) — and rejects plain objects that merely have Error-like prototypes set via `Object.setPrototypeOf` without the native Error brand. The `isPrototypeOf` checks are **subclass-aware**: an instance of `class CustomTypeError extends TypeError {}` has `TypeError.prototype` in its prototype chain and is classified as `TypeError`. `globalThis.TypeError` replacement has no effect because `_TypeErrorProto` was captured before candidate code. `constructor.name` forgery has no effect because `constructor.name` is not consulted. A plain object whose prototype was set to `TypeError.prototype` fails `isNativeError` (no native Error brand) and is reported as `ThrownNonError`. **Same-realm limitation**: `Object.setPrototypeOf(realNativeError, TypeError.prototype)` where `realNativeError` is an existing native Error (e.g. `new Error()`) passes both `isNativeError` and the prototype-identity check; it is classified as `TypeError`. This cannot be resolved in a shared JavaScript realm without out-of-realm isolation. Returning `undefined`, `NaN`, or `Infinity` is reported as `InvalidReturn`, not `TypeError`, so a function that returns `undefined` for non-string inputs cannot satisfy a `{"raises": "TypeError"}` test case.

- **Worker thread execution model**: `_js_runner.js` runs each case in a fresh Worker thread spawned with `eval: true` using the in-memory `WORKER_BOOT` string. The main thread accepts at most one result message per Worker (validated with a per-invocation nonce), terminates the Worker after settlement, and awaits full termination before starting the next case. `process.exit(0)` inside a Worker exits only that Worker; the runner records the case as a failure. This prevents candidate-controlled async work from bleeding between cases.

- **`--sandbox docker`** needs the image from `js.Dockerfile`:
  ```bash
  docker build -f teams/10-post-training/rl/js/js.Dockerfile -t g10-js-rl:1 teams/10-post-training/rl/js
  ```
  (`G10_JS_IMAGE` names another image.) Node.js 26 Active LTS (released 5 May 2026, LTS since 28 Oct 2026, EOL April 2029). The container has no network, a read-only root, no capabilities, 768 MB, 1 CPU, 128 processes, and a 64 MB `/tmp` tmpfs. The work folder (`/work`) is a writable bind mount; the runner writes `results.json` there only after all Workers are terminated. A missing image or daemon raises `RuntimeError` instead of scoring 0.

- **Who wrote the tasks.** The `camel_to_snake` task was written by Ajay Kumar for the TSAI ERA V5 Week 3 assignment. Each `task.json` records the author in `source`. TSAI's data rule (see `../../rl-data/README.md`) allows human-written problems for training; confirm with TSAI before using these tasks in training data.

- Tasks (1): `camel_to_snake`.

## Validation Results

The nine implementation and task files (`js_verifier.py`, `_js_runner.js`, `js.Dockerfile`,
`test_js_verifier.py`, and the five `tasks/camel_to_snake/` files) were validated at commit
`b37c65d982d665a2e1650942e136626cf5448f83`. This README was not part of that snapshot.

**Local process-sandbox run** (Docker unavailable locally):

```
73 passed, 11 skipped
```

The 11 skipped tests are Docker-parametrized variants; they are skipped automatically when
`docker image inspect g10-js-rl:1` fails.

**GitHub Actions run** (Ubuntu 26.04, process + Docker sandboxes):

- Repository: <https://github.com/AjaySnl/g10-week3-js-docker-validation>
- Commit: `b37c65d982d665a2e1650942e136626cf5448f83`
- Run: <https://github.com/AjaySnl/g10-week3-js-docker-validation/actions/runs/44116328031>

```
84 collected, 84 passed, 0 failed, 0 skipped  (44.54 s)
```

| Check | Result |
|---|---|
| Host Node.js | v26.13.1 |
| Docker container Node.js | v26.13.1 |
| Docker image build | passed (`node:26-alpine`, `worker_threads` verified at build time) |
| Process sandbox `check-task` | `task OK` |
| Docker sandbox `check-task` | `task OK` |

The 84-item count versus the local 73-passed/11-skipped count reflects the same 84 collected
tests: on CI both process and Docker variants of the 11 Docker-parametrized tests ran and passed.
