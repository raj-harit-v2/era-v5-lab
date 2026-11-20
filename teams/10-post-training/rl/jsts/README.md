# JavaScript and TypeScript tasks for RL data v1 (`jsts_verifier.py`, `tasks/`)

Gate 3 deliverables "one JavaScript verifier set" and "one TypeScript verifier set": one exact check, one correct
answer, one wrong answer (work order, 14 Nov). Registered as `js/<task_id>` and `ts/<task_id>` in `../reward.py`.
Both languages share one verifier and one sandbox image because they differ only in the file extension and the fence.

```text
rl/jsts/
  README.md                  this file
  jsts_verifier.py           reward(), check_task() and the command line
  build_tasks.py             builds task folders from an Exercism track clone
  jsts.Dockerfile            the sandbox image (node 22, jest 29, babel; network off at run time)
  babel.config.cjs, jest.config.cjs
  test_jsts_verifier.py      reference and wrong answer per task, cheating candidates, lint
  attacks.py                 attack fixtures (candidates that try to forge a report or tamper with the matchers)
  test_jsts_forgery.py       every attack must score 0 in the real sandbox
  tasks/js/<id>/, tasks/ts/<id>/   task.json, prompt.md, stub/<file>, hidden/<spec file>, hidden/<reference file>
```

## How a task is scored

The model sees `prompt.md`: a fixed output-format header, the upstream exercise statement, and the upstream starting
file (the stub). It answers with one fenced `javascript` or `typescript` block holding the whole solution module (the
last such block counts). In a fresh container (network off, 1 GB, 2 CPUs, 256 pids, all capabilities dropped,
non-root) the module is placed next to the hidden spec file and jest runs it. Reward 1 only if every hidden test
passes. The reply never contains test names or expected values, only a reason and a pass count.

Report integrity. An independent attack test (18 Nov 2026) showed that a candidate loaded in the spec's own jest realm can
edit the test registry before the run starts (attack J1: every test's body set to a no-op, the canaries spared by name or
by shape), and no check made inside that realm sees it. So the candidate is no longer loaded there: root compiles it with
babel before jest starts, and the solution file the spec requires is a one-line loader (`membrane.cjs`) that runs the
compiled code in its own V8 context (no `process`, no `require`, no string eval, a no-op `console`) and passes values back
through a copying membrane: primitives, arrays, plain objects, Map, Set and Date are copied into the test realm; functions,
classes and instances are wrapped; thrown values are rebuilt as test-realm errors. Arguments into the candidate are rebuilt
in its realm. The remaining checks do not rely on the sandbox, so they stay as defence in depth:

- The container starts as root with only SETUID, SETGID, CHOWN and DAC_OVERRIDE. Jest runs with workers (not
  `--runInBand`); a setup file drops every worker to the `runner` user before the candidate is loaded (after that the
  worker has no capabilities) and freezes the matcher table (`expect.extend` and `addEqualityTesters` throw).
- The jest parent stays root and prints the JSON report to a root-owned file. The candidate (user `runner`) cannot
  overwrite or race that file, cannot write to the parent's stdout, and cannot signal or trace the parent. The outer
  script reads the report only after jest has exited.
- A sentinel test with a random name, in its own file, must be reported as failed and jest must exit with code 1.
- Four canary tests (random values; `toBe`, `toEqual`, `toStrictEqual`, `toThrow`; each false by construction) are
  appended to the hidden spec, so they run in the same realm as the candidate and must all be reported as failed. A
  candidate that patches matchers or `Object.is` from inside jest makes a canary pass and scores 0.
- The passed tests must equal the count measured on the reference when the task was built, and no other test may
  fail. An empty module, a syntax error, a throw or `process.exit(0)` at import, an endless loop and a candidate that
  replaces `expect`, `test` and `describe` all score 0 (`test_jsts_verifier.py`).

### Attacks tried (`attacks.py`, `test_jsts_forgery.py`; 18 Nov 2026, image `g10-jsts-rl:1`; the first group on task `js/binary`, the second group (`TASK_ATTACKS`, files in `attack_fixtures/`) on its own tasks)

Written after RaviNaik's review of this PR (point 3). Each is a candidate module; "first runner" is the version of
`jsts_verifier.py` before this change (jest `--runInBand`, report written by jest to a path in `/tmp`, readable and
writable by the candidate). Results are the reward returned by the real sandbox.

| Attack | First runner | Now |
|---|---|---|
| lists the cwd, takes the token from `z<token>.spec.js`, writes a forged report in `process.on('exit')` | 0 (the handler never fires inside jest's process copy) | 0 |
| same forged report from `afterAll`, from a timer, by wrapping `process.exit`, by patching the shared `fs.writeFileSync` | 0 (jest writes the true report afterwards, or the sandbox copy of `process` is inert) | 0 |
| detached process that keeps overwriting the report file after jest exits | **1** | 0 (the report is a root-owned file) |
| appends a forged report to the parent's stdout, the log files and the old report path, then stops the parent | 0 (timeout) | 0 |
| `process.setuid(0)` | 0 (already non-root) | 0 (setuid is refused after the drop) |
| `expect.extend` with always-pass matchers | **1** | 0 |
| `expect.addEqualityTesters([() => true])` | **1** | 0 |
| `global.expect = ...` (the spec imports `expect`, so inert) | 0 | 0 |
| reaches the real `Object` through `expect.constructor` and sets `Object.is` to always true | **1** | 0 (canary) |
| the same, but passes only when the values are below 1e8, trying to skip the canaries | **1** | 0 (canary) |

Second group (independent attack test, 18 Nov 2026; against the PR as pushed before this change; files in `attack_fixtures/`,
each starts "ATTACK FIXTURE, never training data"). These act in the spec's own jest realm before the run starts:

| Attack | Before the membrane | Now |
|---|---|---|
| J1 (js, ts): finds jest-circus state through `Symbol(JEST_STATE_SYMBOL)` and sets every test's body to a no-op, sparing the canaries by name | **1** (wrong solution, all checks pass) | 0 |
| J1b: reads the hidden spec from disk, spares the appended `expect(<literal>)` tests by shape, no name pattern | **1** | 0 |
| J1c: J1 without sparing (control) | 0 (canary fires) | 0 |
| J5: realm-escape probe (callsites, `.caller`, constructor chains) | 0 (nothing to escape to) | 0 (no test passes, no escape) |

On the first runner five of these scored 1 without solving the task. The matcher tricks need no sentinel token and no
report path, only the export names that the prompt shows. One verification costs about 0.15 to 0.25 s more than before
(worker start-up and the guard); the membrane adds about 0.15 s (js/matrix reference 0.97 s to 1.16 s, ts/word-count 1.06 s to
1.20 s, same Mac and image, mean of 3); timings are in the PR.

## Data

- Source: Exercism practice exercises, `exercism/javascript` and `exercism/typescript` (MIT; the statements come from
  `exercism/problem-specifications`, also MIT). Statement, stub, reference solution (`.meta/proof.ci.*`) and tests are
  upstream, human-written files. Generator: none. Each `task.json` records the upstream commit, the exercise authors
  and the date the reference was first added.
- Selection: exercises whose reference file was first added on or before 2022-12-31 (before AI-assisted
  contributions were common), one solution file, one spec file, at most 30 tests, no `fs`/`child_process`/network
  import, drawn at random with a seed (`build_tasks.py --pick N --seed 17`), not by reading them. Later edits to those
  files were not audited, and the upstream commit is recorded.
- Hidden spec: the upstream spec with `xtest`, `xit` and `xdescribe` switched on (Exercism ships only the first test
  enabled). The expected test count is measured by running the upstream reference.
- `prompt.md` starts with a fixed output-format header. **The header is harness text, not taken from a source** (the
  output protocol, no task content). TSAI has not ruled on it; if it must be human-written, replace `HEADER` in
  `build_tasks.py` and rebuild.
- Exercism exercises are public and widely copied. They are not an evaluation benchmark of ours, but a base model may
  have seen them, which raises its pass rate on them.

## Commands

```bash
docker build -f teams/10-post-training/rl/jsts/jsts.Dockerfile -t g10-jsts-rl:1 teams/10-post-training/rl/jsts   # once, needs network
python teams/10-post-training/rl/jsts/jsts_verifier.py --check-all       # reference 1, stub 0 for every task
python teams/10-post-training/rl/jsts/jsts_verifier.py --reward teams/10-post-training/rl/jsts/tasks/js/<id> completion.txt
python teams/10-post-training/rl/reward.py --check-all --type js         # or --type ts
python -m pytest teams/10-post-training/rl/jsts/test_jsts_verifier.py -q -p no:cacheprovider
python teams/10-post-training/rl/jsts/build_tasks.py --track javascript --clone <exercism/javascript clone> --slug <slug>
```

## Limits

- Node documents `vm` as not a security boundary. The membrane stops every attack tried (J1, J1b, J1c, J5, a realm-escape
  probe through callsites, `.caller` and constructor chains), but that is not a proof. A task whose tests pass callbacks
  or foreign objects into the candidate (a function argument, for example) throws TypeError at the membrane, so such a
  task needs the membrane extended; its reference check fails until then, and `jsts_verifier.py --check-all` shows it.
- The candidate runs in the container, so it can read the hidden spec file there and could, in
  principle, learn what the tests expect. The sentinel, the canaries and the count checks stop a forged report and
  tampered matchers, not reading the spec. The same limit is stated for SWE environments in `swe-envs/README.md`.
- The canaries have random values, but a candidate that parses the spec file at run time, finds them and special-cases
  them would pass them; no attack of that kind was tried. The report itself cannot be forged by the candidate user,
  and every attack above scores 0, but "scores 0 on these attacks" is not a proof that no other attack exists. In the
  first real run, a pass-rate far above the reference's expectation on a task is a signal to read those replies.
- Exercism exercises are public and may have been seen by the base model. This was not measured. Where it would show
  is the pass rate of the base model on these tasks before RL use: a rate near the ceiling on unseen-style tasks would
  point to memorisation.
- TypeScript is stripped by babel and not type-checked: a type error scores like valid code.
- One test framework (jest) and one source (Exercism); a few tasks per language.
