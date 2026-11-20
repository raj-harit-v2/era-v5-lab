"""Validate the evidence emitted by a finished G5 Week-2 trainer invocation."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re


EVIDENCE_SCOPE = (
    "PASS means the run completed with internally consistent evidence. "
    "This check provides neither a BPB result nor a winning configuration."
)


IDENTITY_FIELDS = (
    "config", "artifacts", "train_sha256", "heldout_sha256",
    "heldout_sources_sha256", "heldout_checksum_sha256", "sources",
    "device", "torch", "smoke",
)


def json_object(line):
    value = json.loads(line)
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_metrics(path, completed, errors):
    steps = Counter()
    count = 0
    with path.open(encoding="utf8") as stream:
        for count, line in enumerate(stream, start=1):
            try:
                step = json_object(line).get("step")
                if type(step) is not int or step < 0:
                    raise ValueError("step must be a nonnegative integer")
            except ValueError as exc:
                errors.append(f"{path.name} row {count}: {exc}")
                continue
            steps[step] += 1
    if completed is not None and count != completed + 1:
        errors.append(f"{path.name}: expected {completed + 1} rows, found {count}")
    duplicates = sorted(step for step, occurrences in steps.items() if occurrences > 1)
    if duplicates:
        errors.append(f"{path.name}: duplicate steps {duplicates}")
    if completed is not None:
        extra = sorted(step for step in steps if step > completed)
        if extra:
            errors.append(f"{path.name}: unexpected steps {extra}")
        # Count gaps before sampling them so a corrupt step budget is cheap to reject.
        missing_count = completed + 1 - (len(steps) - len(extra))
        if missing_count:
            missing = []
            for step in range(completed + 1):
                if step not in steps:
                    missing.append(step)
                    if len(missing) == 10:
                        break
            errors.append(f"{path.name}: {missing_count} missing steps, first {missing}")
    return count


def check_losses(path, completed, errors):
    count = 0
    with path.open(encoding="utf8") as stream:
        for count, line in enumerate(stream, start=1):
            if completed == 0 and count == 1 and line == "\n":
                count = 0
                continue
            try:
                if not math.isfinite(float.fromhex(line.strip())):
                    raise ValueError("expected a finite loss")
            except (ValueError, OverflowError) as exc:
                errors.append(f"{path.name} row {count}: {exc}")
    if completed is not None and count != completed:
        errors.append(f"{path.name}: expected {completed} rows, found {count}")
    return count


def check_checkpoint(path, identity, completed, errors):
    try:
        import torch

        # The native checkpoint includes NumPy/Python RNG objects.
        state = torch.load(path, map_location="cpu", weights_only=False)
        if state["identity_sha256"] != identity:
            errors.append("checkpoint.pt: identity_sha256 differs from manifest")
        if type(state["step"]) is not int or state["step"] != completed:
            errors.append("checkpoint.pt: step differs from summary")
    except Exception as exc:
        errors.append(f"checkpoint.pt: could not inspect checkpoint: {exc}")
        return False
    return True


def validate(run, *, trusted_checkpoint=False, expected_steps=None, verify_inventory=None):
    errors = []
    result = {
        "classification": "unknown",
        "evidence_scope": EVIDENCE_SCOPE,
        "expected_steps": expected_steps,
        "completed_steps": None,
        "row_counts": {},
        "sha256": {},
        "checkpoint_checked": False,
        "errors": errors,
    }

    def read_evidence(name, read):
        path = run / name
        try:
            if not path.is_file() or path.stat().st_size == 0:
                raise ValueError("missing or empty evidence file")
            result["sha256"][name] = file_sha256(path)
            return read(path)
        except (OSError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
            return None

    def read_json(path):
        return json_object(path.read_text(encoding="utf8"))

    manifest = read_evidence("manifest.json", read_json) or {}
    summary = read_evidence("summary.json", read_json) or {}
    identity = None
    try:
        fields = {key: manifest[key] for key in IDENTITY_FIELDS}
        if "bpb_policy" in manifest:
            fields["bpb_policy"] = manifest["bpb_policy"]
        identity = hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()
        if manifest.get("identity_sha256") != identity:
            errors.append("manifest.json: identity_sha256 differs from recorded inputs")
        configured_steps = fields["config"]["run"]["steps"]
        if type(configured_steps) is not int or configured_steps <= 0:
            raise ValueError("config.run.steps must be a positive integer")
        if expected_steps is not None and configured_steps != expected_steps:
            errors.append(f"manifest.json: configured {configured_steps} steps, expected {expected_steps}")
        result["expected_steps"] = configured_steps if expected_steps is None else expected_steps
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"manifest.json: invalid run identity or step budget: {exc}")

    smoke = manifest.get("smoke")
    complete = summary.get("status") == "COMPLETED"
    if smoke is True:
        result["classification"] = "smoke"
        if manifest.get("status") != "SMOKE_NOT_A_QUALITY_RESULT" or summary.get("status") != "SMOKE":
            errors.append("manifest.json and summary.json: inconsistent smoke status")
    elif smoke is False:
        result["classification"] = "quality" if complete else "incomplete"
        if manifest.get("status") != "AGREED_BASELINE_RUN":
            errors.append("manifest.json: expected AGREED_BASELINE_RUN")
        if not complete and summary.get("status") != "INCOMPLETE_NOT_A_RESULT":
            errors.append("summary.json: expected COMPLETED or INCOMPLETE_NOT_A_RESULT")
    else:
        errors.append("manifest.json: smoke must be a boolean")

    if summary.get("eligible_for_quality_comparison") is not (complete and smoke is False):
        errors.append("summary.json: inconsistent quality eligibility")
    if not re.fullmatch(r"[0-9a-f]{64}", str(summary.get("final_model_sha256"))):
        errors.append("summary.json: missing or invalid final_model_sha256")
    if type(summary.get("timed_out")) is not bool or (complete and summary["timed_out"]):
        errors.append("summary.json: inconsistent timed_out flag")
    completed = summary.get("steps")
    if type(completed) is not int or completed < 0:
        errors.append("summary.json: steps must be a nonnegative integer")
        completed = None
    result["completed_steps"] = completed
    budget = result["expected_steps"]
    if completed is not None and budget is not None:
        if completed > budget or (complete and completed != budget):
            errors.append(f"summary.json: completed {completed} steps against a budget of {budget}")

    result["row_counts"]["metrics.jsonl"] = read_evidence(
        "metrics.jsonl", lambda path: check_metrics(path, completed, errors)
    )
    for name in ("losses.txt", "total_losses.txt"):
        result["row_counts"][name] = read_evidence(
            name, lambda path: check_losses(path, completed, errors)
        )
    if smoke is False or (run / "checkpoint.pt").exists():
        def inspect_checkpoint(path):
            if trusted_checkpoint:
                result["checkpoint_checked"] = check_checkpoint(path, identity, completed, errors)
            elif result["classification"] == "quality":
                errors.append(
                    "checkpoint.pt: quality PASS requires identity and step verification. "
                    "Use --trusted-checkpoint only for a checkpoint you trust."
                )

        read_evidence("checkpoint.pt", inspect_checkpoint)
    if verify_inventory is not None:
        try:
            reference = read_json(verify_inventory)["sha256"]
            if not isinstance(reference, dict) or not reference:
                raise ValueError("expected a nonempty sha256 inventory")
            actual = result["sha256"]
            for name in sorted(set(reference) | set(actual)):
                if name not in actual or actual[name] != reference.get(name):
                    errors.append(f"{name}: SHA-256 inventory mismatch")
        except (KeyError, OSError, ValueError) as exc:
            errors.append(f"Reference inventory: {exc}")
    result["valid"] = not errors
    result["quality_ready"] = (
        result["valid"] and result["classification"] == "quality" and result["checkpoint_checked"]
    )
    result["verdict"] = "PASS" if result["quality_ready"] else "FAIL"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--expected-steps", type=int, help="Independently expected training budget")
    parser.add_argument("--json", action="store_true", help="Print the validation report as JSON")
    parser.add_argument("--verify-inventory", type=Path, help="Compare hashes to a prior JSON report")
    parser.add_argument(
        "--trusted-checkpoint", action="store_true",
        help="Inspect checkpoint metadata using PyTorch. Use only with trusted files.",
    )
    args = parser.parse_args()
    if args.expected_steps is not None and args.expected_steps <= 0:
        parser.error("--expected-steps must be positive")
    result = validate(
        args.run_dir, trusted_checkpoint=args.trusted_checkpoint,
        expected_steps=args.expected_steps, verify_inventory=args.verify_inventory,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['verdict']}: {result['classification']} run")
        print(result["evidence_scope"])
        print(f"Completed steps: {result['completed_steps']} / {result['expected_steps']}")
        for name, count in result["row_counts"].items():
            print(f"  {name}: {count} rows")
        print(f"Checkpoint metadata inspected: {result['checkpoint_checked']}")
        for error in result["errors"]:
            print(f"  {error}")
        for name, digest in sorted(result["sha256"].items()):
            print(f"{digest}  {name}")
    return 0 if result["quality_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
