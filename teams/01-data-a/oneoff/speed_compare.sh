#!/usr/bin/env bash
# Check a rule speed-up before you commit it: clean.py output unchanged, harm tests and pytest pass, and how much faster.
# Run it from anywhere, in a plain terminal (not inside VS Code). It writes only to --work, never into the repo, and saves
# everything it prints in $WORK/run-<time>.log.
#
#   oneoff/speed_compare.sh --rules DA-B4-010
#
# Run it BEFORE you commit: "before" is the last commit (HEAD) and "after" is the clean.py in your working copy. If you
# already committed the fix, compare against the commit before it: --before HEAD~1 --after HEAD.
#
# It runs these steps (about 6 to 8 minutes) and ends with a SUMMARY and RESULT: PASS or FAIL:
#   build    clean.py is exactly what build_clean.py makes from the sheet (catches a forgotten rebuild)
#   pytest   the whole test suite
#   trees    $WORK/before and $WORK/after, the two clean.py (stops if they are identical: nothing to compare)
#   speed    output sha256 and docs/s of both on every pack in --packs, then compare (the sha256 must match on all)
#   profile  per-rule time of both on the profile packs (the SUMMARY shows the rule times and the next slowest rules)
#   harm     make_harm_tests.py on both, then diff the results (only rules_file_sha256 may differ)
#   count    how many documents --rules fix or drop on the count packs (the "docs changed" figure)
# To repeat only some steps, name them: speed_compare.sh --rules DA-B4-010 speed profile
#
# Options (or the environment variable in brackets):
#   --rules IDS    the rule(s) you changed, comma separated (needed for count and the rule times in the SUMMARY)
#   --before REV   revision whose clean.py is "before"                  [BEFORE, default HEAD]
#   --after REV    revision for "after", or "worktree" = your working copy [AFTER, default worktree]
#   --before-clean FILE, --after-clean FILE   use this clean.py instead of the one in that revision, for a change that is
#                  in a sheet but not yet in the committed clean.py (for example a rule of spec_v1_1/sheets/specv1_1.md:
#                  build_clean.py --sheet ... --out FILE, once from the sheet as committed and once from the edited sheet).
#                  The build step then checks the after file against --sheet.
#   --packs DIR    <pack_id>.parquet files                              [PACKS, default <repo parent>/week1-packs]
#   --work DIR     trees, results and logs                              [WORK, default <repo parent>/scratchpad/clean-speed]
#   --limit N      speed, profile and count use only the first N docs of each pack (default all; for large packs)
#   --profile-packs "p1 p2"  packs to profile and report docs/s for     (default: the first 2 packs the rule runs on)
#   --count-packs "p1 p2"    packs to count on                          (default: every pack the rule runs on)
#   --sheet FILE   sheet the build step builds clean.py from, if not spec_v1_1/sheets/specv1_1.md, the default of
#                  build_clean.py (for example the frozen spec_v1/sheets/specv1.md); relative to the current folder, or
#                  absolute  [SHEET]
#   --include-all  speed also runs ind-mr-sangraha-v, which is left out by default (use with a folder of Indic packs)
#   --expected-packs "p1 p2" exact required speed/harm inventory (default: original 13; --include-all: all registered packs)
# Python with pyarrow: the PY environment variable (default: the era5 conda python).
set -u
set -o pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(git -C "$HERE" rev-parse --show-toplevel)"
TEAM="$(dirname "${HERE#"$REPO"/}")"                      # teams/01-data-a
PARENT="$(dirname "$REPO")"
BEFORE="${BEFORE:-HEAD}"; AFTER="${AFTER:-worktree}"
PACKS="${PACKS:-$PARENT/week1-packs}"; WORK="${WORK:-$PARENT/scratchpad/clean-speed}"
PY="${PY:-/home/forest/miniconda3/envs/era5/bin/python}"
SHEET="${SHEET:-}"; BEFORE_CLEAN=""; AFTER_CLEAN=""
RULES=""; LIMIT=0; STAGES=(); PROFILE_PACKS=(); COUNT_PACKS=(); EXCLUDE=(ind-mr-sangraha-v); EXPECTED_PACKS=()
help() { awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; }
while [ $# -gt 0 ]; do
  case "$1" in
    --rules) RULES="$2"; shift 2;; --before) BEFORE="$2"; shift 2;; --after) AFTER="$2"; shift 2;;
    --packs) PACKS="$2"; shift 2;; --work) WORK="$2"; shift 2;; --limit) LIMIT="$2"; shift 2;;
    --profile-packs) read -ra PROFILE_PACKS <<< "$2"; shift 2;; --count-packs) read -ra COUNT_PACKS <<< "$2"; shift 2;;
    --sheet) SHEET="$2"; shift 2;;
    --before-clean) BEFORE_CLEAN="$2"; shift 2;; --after-clean) AFTER_CLEAN="$2"; shift 2;;
    --include-all) EXCLUDE=(); shift;;
    --expected-packs) read -ra EXPECTED_PACKS <<< "$2"; shift 2;;
    -h|--help) help; exit 0;;
    -*) echo "unknown option $1" >&2; exit 2;; *) STAGES+=("$1"); shift;;
  esac
done
[ ${#STAGES[@]} -eq 0 ] && STAGES=(build pytest trees speed profile harm count)
SHEET_ARGS=()
if [ -n "$SHEET" ]; then
  [ -f "$SHEET" ] || { echo "--sheet: no such file: $SHEET" >&2; exit 2; }
  SHEET="$(cd "$(dirname "$SHEET")" && pwd)/$(basename "$SHEET")"; SHEET_ARGS=(--sheet "$SHEET")
fi
mkdir -p "$WORK"
LOG="$WORK/run-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee "$LOG") 2>&1
echo "log: $LOG"
for f in BEFORE_CLEAN AFTER_CLEAN; do      # a clean.py given on the command line, as an absolute path
  [ -z "${!f}" ] && continue
  [ -f "${!f}" ] || { echo "--${f%_CLEAN}-clean: no such file: ${!f}" >&2; exit 2; }
  printf -v "$f" '%s' "$(cd "$(dirname "${!f}")" && pwd)/$(basename "${!f}")"
done
CLEAN="${AFTER_CLEAN:-$REPO/$TEAM/spec_v1/clean.py}"; CHECK="$HERE/speed_check.py"; FAIL=0
PIN=(); command -v taskset >/dev/null && PIN=(taskset -c 0)          # CPU 0 and 1 are one physical core on the author's laptop
EXCL=(); [ ${#EXCLUDE[@]} -gt 0 ] && EXCL=(--exclude "${EXCLUDE[@]}")
LIM=();  [ "$LIMIT" -gt 0 ] && LIM=(--limit "$LIMIT")
if [ ${#EXPECTED_PACKS[@]} -eq 0 ]; then
  if [ ${#EXCLUDE[@]} -eq 0 ]; then
    read -ra EXPECTED_PACKS <<< "$("$PY" -I - "$CLEAN" <<'EOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("clean", sys.argv[1]); clean = importlib.util.module_from_spec(spec); spec.loader.exec_module(clean)
print(" ".join(sorted(clean._FAMILY)))
EOF
)"
  else
    read -ra EXPECTED_PACKS <<< "code-cpp code-go code-java code-js-ts code-python code-rust en-dclm en-fineweb-edu en-nemotroncc en-nemotroncc-synth math-finemath math-megamath sci-finepdfs"
  fi
fi
BUILD_RESULT="not run"; PYTEST_LINE="not run"; HARM_RESULT="not run"; SPEED_RAN=0; PROFILE_RAN=0; COUNT_RAN=0
say() { printf '\n== %s\n' "$*"; }
tree() { echo "$WORK/$1/$TEAM/spec_v1"; }
need_trees() { [ -f "$(tree before)/clean.py" ] && [ -f "$(tree after)/clean.py" ] || { echo "run the trees step first"; exit 1; }; }

# the packs the first rule runs on (its SCOPE in clean.py) that exist in --packs: the defaults for profile and count
if [ -n "$RULES" ] && { [ ${#PROFILE_PACKS[@]} -eq 0 ] || [ ${#COUNT_PACKS[@]} -eq 0 ]; }; then
  read -ra RULE_PACKS <<< "$(PYTHONDONTWRITEBYTECODE=1 "$PY" -I - "$CLEAN" "$PACKS" "${RULES%%,*}" <<'EOF'
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("clean", sys.argv[1]); c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
have = {p.stem for p in Path(sys.argv[2]).glob("*.parquet")}
print(" ".join(sorted(p for p in c.SCOPE.get(sys.argv[3], ()) if p in have)))
EOF
)"
  [ ${#PROFILE_PACKS[@]} -eq 0 ] && PROFILE_PACKS=("${RULE_PACKS[@]:0:2}")
  [ ${#COUNT_PACKS[@]} -eq 0 ] && COUNT_PACKS=("${RULE_PACKS[@]}")
fi
[ ${#PROFILE_PACKS[@]} -eq 0 ] && PROFILE_PACKS=(en-dclm en-fineweb-edu)
[ ${#COUNT_PACKS[@]} -eq 0 ] && COUNT_PACKS=("${PROFILE_PACKS[@]}")
echo "sheet for the build step: ${SHEET:-default (spec_v1_1/sheets/specv1_1.md)}"
echo "rules: ${RULES:-none}; before: $BEFORE; after: $AFTER; profile packs: ${PROFILE_PACKS[*]}; count packs: ${COUNT_PACKS[*]}"

stage_build() {
  say "build: clean.py is the fresh build of ${SHEET:-spec_v1_1/sheets/specv1_1.md}"
  if "$PY" -I "$REPO/$TEAM/spec_v1/build/build_clean.py" "${SHEET_ARGS[@]}" --out "$WORK/fresh_clean.py" >/dev/null && cmp -s "$WORK/fresh_clean.py" "$CLEAN"; then
    BUILD_RESULT="ok, clean.py $(sha256sum "$CLEAN" | cut -c1-12) is the fresh build of ${SHEET:-specv1_1.md}"
  else
    BUILD_RESULT="FAIL: clean.py differs from a fresh build. Run: python -I $TEAM/spec_v1/build/build_clean.py ${SHEET_ARGS[*]}"; FAIL=1
  fi
  echo "$BUILD_RESULT"
}

stage_pytest() {
  say "pytest: the whole suite"
  local out status=0; out="$(cd "$REPO" && "$PY" -m pytest "$TEAM/tests" -q -p no:cacheprovider 2>&1)" || status=$?
  PYTEST_LINE="$(echo "$out" | tail -1)"
  if [ "$status" -ne 0 ]; then FAIL=1; echo "$out" | tail -15; else echo "$PYTEST_LINE"; fi
}

stage_trees() {
  say "trees: before = $BEFORE, after = $AFTER"
  rm -rf "$WORK/before" "$WORK/after"; mkdir -p "$WORK/before" "$WORK/after"
  local rev="$AFTER"; [ "$AFTER" = worktree ] && rev=HEAD
  git -C "$REPO" archive "$rev" | tar -x -C "$WORK/after"
  [ "$AFTER" = worktree ] && cp "$CLEAN" "$(tree after)/clean.py"
  [ -n "$AFTER_CLEAN" ] && cp "$AFTER_CLEAN" "$(tree after)/clean.py"
  cp -r "$WORK/after/." "$WORK/before/"
  if [ -n "$BEFORE_CLEAN" ]; then cp "$BEFORE_CLEAN" "$(tree before)/clean.py"
  else git -C "$REPO" show "$BEFORE:$TEAM/spec_v1/clean.py" > "$(tree before)/clean.py" || { echo "no clean.py at $BEFORE"; exit 1; }; fi
  local b a; b="$(sha256sum "$(tree before)/clean.py" | cut -c1-12)"; a="$(sha256sum "$(tree after)/clean.py" | cut -c1-12)"
  echo "  before $b   after $a"
  if [ "$b" = "$a" ]; then
    echo "STOP: before and after are the same clean.py, so there is nothing to compare (the fix may already be committed)."
    echo "      Compare with the commit before it: --before HEAD~1 --after HEAD"
    FAIL=1; summary; exit 1
  fi
}

stage_speed() {
  need_trees; say "speed: output sha256 and docs/s on $PACKS (excluding: ${EXCLUDE[*]:-nothing}; limit: ${LIMIT} docs per pack, 0 = all)"
  SPEED_RAN=1
  for side in before after; do
    "${PIN[@]}" "$PY" -I "$CHECK" run --clean-dir "$(tree $side)" --packs "$PACKS" "${EXCL[@]}" "${LIM[@]}" \
      --repeat 3 --progress 0 --out "$WORK/$side.json" 2> "$WORK/$side.log" || { echo "$side run failed, see $WORK/$side.log"; FAIL=1; return; }
    echo "  $side done"
  done
  "$PY" -I "$CHECK" compare "$WORK/before.json" "$WORK/after.json" --md "$WORK/speed_table.md" --expected-packs "${EXPECTED_PACKS[@]}" || FAIL=1
}

stage_profile() {
  need_trees; say "profile: per-rule time on ${PROFILE_PACKS[*]}, one core (top 10 rules)"
  PROFILE_RAN=1; mkdir -p "$WORK/profile"
  for pack in "${PROFILE_PACKS[@]}"; do
    local src="$PACKS/$pack.parquet"
    if [ "$LIMIT" -gt 0 ]; then       # --limit: profile the first N docs only (a small file named <pack>.parquet, as run_clean.py wants)
      mkdir -p "$WORK/slices"
      "$PY" -I - "$src" "$WORK/slices/$pack.parquet" "$LIMIT" <<'EOF'
import sys, pyarrow.parquet as pq
pq.write_table(pq.read_table(sys.argv[1]).slice(0, int(sys.argv[3])), sys.argv[2])
EOF
      [ $? -eq 0 ] || { echo "slice failed: $pack"; FAIL=1; return; }
      src="$WORK/slices/$pack.parquet"
    fi
    for side in before after; do
      "${PIN[@]}" "$PY" -I "$(tree $side)/run_clean.py" --pack "$src" \
        --out "$WORK/profile/$side-$pack" 2> "$WORK/profile/$side-$pack.log" >/dev/null || { echo "profile failed: $side $pack"; FAIL=1; return; }
      echo "  profiled $side $pack (full table: $WORK/profile/$side-$pack.log)"
    done
  done
}

stage_harm() {
  need_trees; say "harm: make_harm_tests.py on both trees (a few minutes)"
  mkdir -p "$WORK/harm/before" "$WORK/harm/after"; local pids=()
  for side in before after; do
    "$PY" -I "$(tree $side)/validate/make_harm_tests.py" "$WORK/after" "$PACKS" \
      --out "$WORK/harm/$side/harm_tests.md" --results "$WORK/harm/$side/results" > "$WORK/harm/$side.log" 2>&1 &
    pids+=($!)
  done
  local exited=0
  for p in "${pids[@]}"; do wait "$p" || exited=1; done     # make_harm_tests.py exits 1 when a pack fails its own harm limit
  for side in before after; do
    [ -f "$WORK/harm/$side/harm_tests.md" ] || { echo "a harm run failed, see $WORK/harm/*.log"; HARM_RESULT="FAIL: a run failed"; FAIL=1; return; }
  done
  [ $exited -eq 0 ] || echo "(a harm run exited with 1: some pack fails its own harm limit, in the logs; what is compared is that the results are the same before and after)"
  echo "-- per-pack result files, ignoring rules_file_sha256 (the clean.py hash):"
  local bad=0
  "$PY" -I - "$WORK/harm/before/results" "$WORK/harm/after/results" "${EXPECTED_PACKS[@]}" <<'EOF' || bad=1
import json, sys
from pathlib import Path
before, after = (Path(p) for p in sys.argv[1:3])
expected = {f"specv1_{p}_harm.json" for p in sys.argv[3:]}
if not expected or {p.name for p in before.glob("*.json")} != expected or {p.name for p in after.glob("*.json")} != expected:
    sys.exit("harm result inventory differs from expected packs")
for name in sorted(expected):
    b, a = (json.loads((folder / name).read_text()) for folder in (before, after))
    b.pop("rules_file_sha256", None)
    a.pop("rules_file_sha256", None)
    if b != a:
        sys.exit(f"harm differs: {name}")
EOF
  if [ $bad -eq 0 ]; then HARM_RESULT="unchanged: all result files identical (every gold changed/dropped count and PASS)"
  else HARM_RESULT="DIFFERS in some result files, see above"; FAIL=1; fi
  echo "  $HARM_RESULT"
  echo "-- harm_tests.md diff (nothing is expected; Indic lines only if the Indic scope changed between the two revisions):"
  diff "$WORK/harm/before/harm_tests.md" "$WORK/harm/after/harm_tests.md" | cut -c1-200 || true
}

stage_count() {
  need_trees; say "count: documents ${RULES:-?} fix or drop, on ${COUNT_PACKS[*]} (the after tree)"
  [ -n "$RULES" ] || { echo "count needs --rules"; FAIL=1; return; }
  COUNT_RAN=1
  "$PY" -I "$CHECK" count --clean-dir "$(tree after)" --packs "$PACKS" --rules "$RULES" --only "${COUNT_PACKS[@]}" "${LIM[@]}" \
    | tee "$WORK/count.txt" || FAIL=1
}

summary() {
  say "SUMMARY (the figures for the speed-log entry)"
  echo "rule(s): ${RULES:-not given (pass --rules to get their time and docs changed)}"
  echo "build:   $BUILD_RESULT"
  echo "pytest:  $PYTEST_LINE"
  echo "harm:    $HARM_RESULT"
  if [ $SPEED_RAN -eq 1 ] || [ $PROFILE_RAN -eq 1 ]; then
    "$PY" -I - "$WORK" "$RULES" "${PROFILE_PACKS[*]}" "$SPEED_RAN" "$PROFILE_RAN" <<'EOF'
import json, sys
work, rules, packs, speed, profile = sys.argv[1], [r for r in sys.argv[2].split(",") if r], sys.argv[3].split(), sys.argv[4] == "1", sys.argv[5] == "1"
def load(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None
if speed:
    b, a = load(f"{work}/before.json"), load(f"{work}/after.json")
    if b and a:
        common = [p for p in b["packs"] if p in a["packs"]]
        same = sum(b["packs"][p]["output_sha256"] == a["packs"][p]["output_sha256"] for p in common)
        print(f"clean.py {b['clean_py_sha256'][:12]} -> {a['clean_py_sha256'][:12]}")
        print(f"output sha256: the same on {same} of {len(common)} packs" + ("" if same == len(common) else "   <-- DIFFERENT"))
        for p in packs:
            if p in common:
                x, y = b["packs"][p]["docs_per_s"], a["packs"][p]["docs_per_s"]
                print(f"docs/s {p}: {x} -> {y} ({y / x:.2f}x)")
if profile:
    for rule in rules:
        for p in packs:
            ms = []
            for side in ("before", "after"):
                s = load(f"{work}/profile/{side}-{p}/{p}_summary.json")
                e = (s or {}).get("rule_seconds", {}).get(rule)
                ms.append(f"{e['ms_per_call']:.3f}" if e else "n/a")
            print(f"rule time {rule} on {p}: {ms[0]} -> {ms[1]} ms/doc")
    for p in packs:   # the slowest rules left (not the ones just changed): the next targets
        s = load(f"{work}/profile/after-{p}/{p}_summary.json")
        rs = (s or {}).get("rule_seconds", {})            # slowest first
        total = sum(v["seconds"] for v in rs.values()) or 1
        top = [(r, v) for r, v in rs.items() if r not in rules][:3]
        print(f"next slowest on {p}: " + ", ".join(f"{r} {v['seconds'] / total:.1%} ({v['ms_per_call']:.3f} ms/doc)" for r, v in top))
EOF
  fi
  [ $COUNT_RAN -eq 1 ] && { echo "documents changed (after tree):"; sed 's/^/  /' "$WORK/count.txt"; }
  if [ $FAIL -eq 0 ]; then echo "RESULT: PASS (every step that ran passed)"; else echo "RESULT: FAIL (see the lines above)"; fi
}

for s in "${STAGES[@]}"; do
  case "$s" in
    build|pytest|trees|speed|profile|harm|count) "stage_$s";;
    *) echo "unknown step $s (build pytest trees speed profile harm count)" >&2; exit 2;;
  esac
done
summary
echo "log: $LOG"
[ $FAIL -eq 0 ]
