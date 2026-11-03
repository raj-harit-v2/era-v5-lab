"""Write the eval-mini v0 items as a self-contained question file, for pipelines that do not run lm-eval
(for example Team 12's quantize_eval.py, which serves GGUF models with llama.cpp and expects --eval <items file>).

Usage (from this folder):
    python make_eval_mini_items.py                 # -> runs/eval_mini_v0_items.json (1,100 items)
    python make_eval_mini_items.py --skip-gated    # without MILU (needs Hugging Face access to ai4bharat/MILU)

The items are the exact documents listed in eval_mini_v0_spec.json, loaded through lm-eval's task configs. Each task's
items are hashed the same way the spec was built; if a hash differs (the hub dataset changed), nothing is written.
The output contains benchmark questions and answers: keep it local. It is gitignored; never commit or redistribute it.

Output schema: {"canary", "name", "spec_sha256", "counts", "items": [{"canary", "id", "question", "choices", "answer", "kind", "subset"}]}
  "canary" is the lab canary line (../decontam/lab_canary.py), in the file and in every item, so a copied item is found too.
  kind "mcq": choices is a list and answer is a letter (A, B, ...); kind "numeric": answer is the final number (GSM8K).
Code tasks (HumanEval+, MBPP+) are not included: they need execution, see run_codegen.py and code_eval_colab.ipynb.
"""
import argparse
import hashlib
import json

from lm_eval.tasks import TaskManager, get_task_dict

from make_eval_mini_spec import items_sha256
from run_lm_eval import HERE, RUNS, stamp  # stamp: the lab canary (../decontam/lab_canary.py)

LETTERS = "ABCDEFGHIJ"
GATED = {"ai4bharat/MILU"}


def to_item(task, doc_id, doc):
    """One document in the schema above. Raises if a document does not have the expected fields."""
    if task == "leaderboard_mmlu_pro":
        choices = list(doc["options"])
        answer = doc["answer"]
        assert answer == LETTERS[int(doc["answer_index"])], (task, doc_id)
        return dict(question=doc["question"], choices=choices, answer=answer, kind="mcq", subset=f"mmlu_pro/{doc['category']}")
    if task == "gsm8k":
        return dict(question=doc["question"], choices=None, answer=doc["answer"].split("####")[-1].strip(), kind="numeric", subset="gsm8k")
    if task.startswith("belebele_"):
        choices = [doc[f"mc_answer{i}"] for i in range(1, 5)]
        question = f"{doc['flores_passage']}\n\n{doc['question']}"
        return dict(question=question, choices=choices, answer=LETTERS[int(doc["correct_answer_num"]) - 1], kind="mcq",
                    subset=f"belebele/{doc['dialect']}")
    if task.startswith("milu_"):
        choices = [doc[f"option{i}"] for i in range(1, 5)]
        return dict(question=doc["question"], choices=choices, answer=LETTERS[int(doc["target"].removeprefix("option")) - 1], kind="mcq",
                    subset=f"milu/{doc['language']}/{doc['subject']}")
    raise ValueError(f"no item mapping for task {task}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(HERE / "eval_mini_v0_spec.json"))
    ap.add_argument("--out", default=str(RUNS / "eval_mini_v0_items.json"))
    ap.add_argument("--skip-gated", action="store_true", help="leave out tasks on gated datasets (MILU)")
    a = ap.parse_args()

    spec_bytes = open(a.spec, "rb").read()
    spec = json.loads(spec_bytes)
    tasks = {t: v for t, v in spec["tasks"].items() if not (a.skip_gated and v["dataset"] in GATED)}
    task_objs = get_task_dict(list(tasks), TaskManager(include_path=str(HERE / "tasks")))

    items, counts = [], {}
    for task, v in tasks.items():
        docs = list(task_objs[task].eval_docs)
        if len(docs) != v["n_test_docs"]:
            raise SystemExit(f"{task}: {len(docs)} test docs, spec says {v['n_test_docs']}; dataset changed, not writing")
        got = items_sha256(docs, v["doc_ids"])
        if got != v["items_sha256"]:
            raise SystemExit(f"{task}: items sha256 {got[:12]} != spec {v['items_sha256'][:12]}; dataset changed, not writing")
        for doc_id in v["doc_ids"]:
            items.append(stamp({"id": f"{task}/{doc_id}", **to_item(task, doc_id, docs[doc_id])}))
        counts[task] = len(v["doc_ids"])
        print(f"{task:22s} {len(v['doc_ids']):4d} items  sha256 ok", flush=True)

    out = stamp({"name": f"eval-mini v0 items ({sum(counts.values())}{', MILU skipped' if a.skip_gated else ''})",
                 "spec_sha256": hashlib.sha256(spec_bytes).hexdigest(), "counts": counts,
                 "note": "benchmark items: keep local, never commit or redistribute", "items": items})
    RUNS.mkdir(parents=True, exist_ok=True)
    # Pure ASCII (\\uXXXX escapes): readers that open the file without encoding="utf-8" still parse it on Windows,
    # where the default is cp1252 (Team 12's load_eval in PR #49 does this). The data is unchanged.
    with open(a.out, "w", encoding="ascii", newline="\n") as f:
        json.dump(out, f, ensure_ascii=True, indent=1)
    print(f"wrote {a.out}: {len(items)} items", flush=True)


if __name__ == "__main__":
    main()
