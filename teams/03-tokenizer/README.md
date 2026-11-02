# Team 03-tokenizer

Put your work in a **topic folder**: `teams/03-tokenizer/<topic>/<file>`, for example `teams/03-tokenizer/harness/run.py`.
Team documents named in the week plan (for example `benchmarks_v1.md`) may sit directly in the team folder. The team lead decides the topic names. Do not make personal folders. Do not make new folders under `teams/`.
Open a pull request; the lead reviews and merges it. The pr-guard check must pass.

## Status (updated 31 Oct 2026)

Each task is a GitHub issue titled `[G3] ...`. The issue is the source of truth; this table is the index.
[All G3 issues](https://github.com/theschoolofai/era-v5-lab/issues?q=is%3Aissue+%5BG3%5D+in%3Atitle)

### Open tasks

| Issue | Task | Owner | State |
|---|---|---|---|
| - | FLORES harness on v2 | @riyaagrahari | open |
| - | TSAI job: fresh C3 sample-v0 build gives sha256 `15468e66…` (Gate 2 evidence), `jobs/2026-11-02-c3-s0-rebuild.md` | @sohamniyogi | job requested |

### Done

| PR | What | By |
|---|---|---|
| #72 | Baseline reproduced: BrahmicTokenizer-131K, FLORES mean fertility 2.8355 (exact match) | @HariniJasti |
| #107 | v0: reserved special slots named (G10, lang, ctrl blocks) | @rjvim |
| #108 | Harness, `train_bpe.py` with fixed script slots, c0 build, COMPARE.md | @sohamniyogi |
| #134 | v1 idea 2: Unicode normalizer (NFC + chillu + Bn/Pa nukta re-join), no id changes (closes #129) | @HariniJasti |
| #137 | `train_bpe --special-layout v0` (closes #127) and v1-c1 retrain: mean Indic −16.97% vs v0 (closes #128) | @sohamniyogi |
| #145 | COMPARE.md: v0 per-language results table (closes #131) | @HariniJasti |
| #147 | Sarvam-m vs Tekken structural identity: same BPE table, 6 renamed specials, ids 10-19 shifted (closes #130) | @riyaagrahari |
| #166 | v2: o200k pruning by usage (13,850 never-used base tokens swapped for English/code o200k tokens; specials and all script ids unchanged), slot split chosen on held-out FineWeb-2: held-out English +1.74% → −0.10% vs baseline, no Indic language worse than v1-c1; counts as C3, sha256 sent to G4 (closes #163) | @sohamniyogi |
| #173 | v0.1: G10 ChatML v0 markers, `g10_slot_00..04` renamed in place to `<|endoftext|>`, `<|think|>`, `<|/think|>`, `<|/tool_call|>`, `<|/tool_result|>`; ids and `special: true` unchanged, sha256 `a33c9907…e578` (closes #132) | @sohamniyogi |
| #183 | Week-2 candidates (closes #182) with v0.1 specials: C1 (o200k swap only), C2 (+slots_v1), C3 (+normalizer v1 = v2); manifests with corpus hashes in `train/` | @sohamniyogi |
| #195 | C1–C3 retrained with the week-2 tokenizer sample v0: per-script text mix (`mix_search.py`, `train_bpe.py --mix`), Devanagari, Gujarati and Oriya changed; check mean Indic −0.12%, sample held-out −0.36% vs the committed C1–C3, no language worse beyond 3 tokens; manifests `train/c*_s0_manifest.json` | @sohamniyogi |

### Areas

| Area | Folder | Owner |
|---|---|---|
| Baseline and COMPARE.md | `baseline/`, `COMPARE.md` | @HariniJasti |
| Harness | `harness/` | @riyaagrahari |
| Training (`train_bpe.py`, c0, v1 retrain) | `train/` | @sohamniyogi |
| v0 special slots | `v0/` | @rjvim |

### Decisions (do not change without a team note)

- Vocab size stays **131,072**, so G4 can size the embedding now.
- Ids **130822-131071** are reserved specials: `g10_slot` 130822-130885, `lang_slot` 130886-130917, `ctrl_slot` 130918-130949, `reserved_128..249` 130950-131071. See `v0/special_slots.md`.
- v1 and later keep every special id. Fill a slot by renaming its string only and keep `special: true`. Never reuse an id a model was trained with.
- Eval text (FLORES-200, IN22, HumanEval, MBPP, GSM8K) is never used for training.
- Pass bar (COMPARE.md): beat BrahmicTokenizer-131K on mean Indic fertility, at most 2% worse on English, HumanEval and MBPP.

### Dates (IST)

- **Sat 31 Oct:** G10 special-token list received; v0.1 merged (#173, closes #132).
- **Sat 31 Oct, 23:59:** diagnosis due for everyone (all rows + medicine sheet).
- **Wed 4 Nov:** C1 and C2 due.

### Keeping this current

- Starting a task: comment on its issue. New task: open a `[G3] ...` issue and add a row here in your next PR.
- Your PR says `Closes #NNN`. In the same PR, move the row from Open to Done.
- Blocked: say so on the issue and change State here.
