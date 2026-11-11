#!/usr/bin/env python3
"""Load Team 5 JSONL experiment logs and Team 6 benchmark run JSON/JSONL files into ClickHouse.

Usage:
    python -I teams/08-monitoring/clickhouse/load_jsonl.py --defaults
    python -I teams/08-monitoring/clickhouse/load_jsonl.py \
        teams/05-architecture/experiments/evidence/run_a/ \
        teams/05-architecture/experiments/evidence/run_b/ \
        teams/06-performance/results/modal_gpu/h200_v1.json
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_CH_URL = os.environ.get("CLICKHOUSE_URL", "http://127.0.0.1:8123")
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]

DEFAULT_SOURCES = (
    "teams/05-architecture/experiments/evidence/run_a/metrics.jsonl",
    "teams/05-architecture/experiments/evidence/run_b/metrics.jsonl",
    "teams/06-performance/results/modal_gpu/h200_v1.json",
)

EPOCH_BASE = datetime(2026, 10, 28, 0, 0, 0, tzinfo=timezone.utc)


def ch_Exec(sql: str, data: bytes | None = None, url: str = DEFAULT_CH_URL) -> str:
    """Execute a SQL statement (with optional POST body) against ClickHouse over HTTP."""
    params = urllib.parse.urlencode({"wait_end_of_query": 1})
    req_url = f"{url.rstrip('/')}/?{params}"
    body = sql.encode("utf-8") if data is None else sql.encode("utf-8") + b"\n" + data
    req = urllib.request.Request(req_url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ClickHouse HTTP {exc.code}: {detail.strip()}") from exc


def execute_sql_file(path: Path, url: str = DEFAULT_CH_URL) -> None:
    """Execute each semicolon-terminated statement in a .sql file."""
    text = path.read_text(encoding="utf-8")
    lines = [
        line for line in text.splitlines()
        if not line.strip().startswith("--")
    ]
    cleaned = "\n".join(lines)
    for stmt in cleaned.split(";"):
        stmt = stmt.strip()
        if stmt:
            ch_Exec(stmt, url=url)


def ensure_schema(url: str = DEFAULT_CH_URL) -> None:
    schema_path = HERE / "schema_v1.sql"
    rollups_path = HERE / "rollups_v1.sql"
    if schema_path.exists():
        execute_sql_file(schema_path, url=url)
    if rollups_path.exists():
        execute_sql_file(rollups_path, url=url)


def _format_utc(dt: datetime) -> str:
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt_utc.microsecond // 1000:03d}"


def _parse_time(raw_time: object, fallback_dt: datetime) -> datetime:
    if isinstance(raw_time, (int, float)) and not isinstance(raw_time, bool) and math.isfinite(raw_time):
        return datetime.fromtimestamp(float(raw_time), tz=timezone.utc)
    if isinstance(raw_time, str) and raw_time.strip():
        s = raw_time.strip()
        if s.endswith(" UTC"):
            s = s[:-4] + "+00:00"
        elif s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    return fallback_dt


def _to_nullable_float(val: object) -> float | None:
    """Convert a JSON scalar to a finite float, or None for null / NaN / Inf."""
    if val is None:
        return None
    if isinstance(val, bool):
        return 1.0 if val else 0.0
    if isinstance(val, (int, float)):
        f = float(val)
        return f if math.isfinite(f) else None
    if isinstance(val, str):
        s = val.strip().lower()
        if s in ("nan", "inf", "-inf", "+inf", "infinity", "-infinity", "null", "none", ""):
            return None
        try:
            f = float(s)
            return f if math.isfinite(f) else None
        except ValueError:
            return None
    return None


_FALLBACK_SOURCES: dict[str, str] = {
    "teams/06-performance/results/modal_gpu/h200_v1.json": (
        '{"meta":{"tag":"h200_v1","time":"2026-10-29 04:16:59 UTC"},"clean":{"step_ms":{"median":401.9842834472656,'
        '"p10":311.0815093994141,"p90":575.1859008789063,"iqr":185.2740478515625,"min":283.072265625,'
        '"max":755.0838623046875,"n":150,"spread_pct":65.70017842852775,"mean":435.52617411295574,'
        '"std":106.66553369549369},"data_ms":{"median":0.678263000001067,"p10":0.5432529000032105,'
        '"p90":0.8128148999993812,"iqr":0.10432849999020277,"min":0.467946000000552,"max":1.0462949999947568,'
        '"n":150,"spread_pct":39.742990550235916,"mean":0.6837142199998899,"std":0.10317487646202185},'
        '"raw_step_ms":[610.6092,548.9005,605.7894,609.2919,584.7405,571.1521,585.268,570.7959,586.2277,659.5663,'
        '639.7747,625.855,680.3047,755.0839,624.6299,589.5931,538.8127,569.5682,551.0865,559.8695,542.6035,579.2385,'
        '528.4768,513.6493,519.9686,502.2139,576.1603,471.9011,507.898,538.4313,542.7569,541.3153,533.1167,546.3975,'
        '557.3803,498.0897,522.1113,557.9304,516.1769,493.283,508.8932,505.4116,503.3607,540.2335,575.0776,513.5171,'
        '552.8945,488.1281,497.7777,473.99,482.4894,460.4302,522.7407,498.9894,505.3791,460.4513,503.6209,551.9559,'
        '522.015,516.5878,519.3747,551.5395,487.4772,517.4674,440.8665,416.9899,454.4713,436.3202,446.8378,397.7511,'
        '424.8499,378.3404,397.4096,373.8252,393.8678,400.7317,426.7924,387.233,447.5753,392.2822,367.7896,371.9255,'
        '420.4929,347.28,393.5083,403.4451,391.2511,358.7971,373.8509,392.2494,402.2674,401.7012,368.5953,334.4713,'
        '354.6685,368.5645,301.5601,385.1046,316.5968,363.3188,365.5314,328.1023,393.2366,382.7343,333.818,346.2443,'
        '351.7154,320.592,357.8858,371.0819,348.8647,336.465,328.4381,332.7229,330.8964,332.5797,345.0692,337.8579,'
        '311.2434,329.7793,353.3132,309.6241,357.6146,294.6759,312.1795,331.0719,284.7382,364.4319,316.6515,328.3834,'
        '295.306,283.0723,284.4105,330.8655,308.9001,303.7603,294.8187,297.086,320.771,352.9677,317.6263,303.821,'
        '327.8393,349.8859,324.1787,293.3077,293.533,329.3703,297.0217,333.4379]},"metrics":{"tokens_per_step":16384,'
        '"tokens_per_s":40757.812368923966,"model_flops_per_token":321957888,"hw_flops_per_token":409565366.8125,'
        '"params_total":79862216,"params_active":51300352,"peak_tflops":989,"model_tflops_per_s":13.122299189799037,'
        '"mfu":0.013268249939129461,"hfu":0.016878653562541347},"memory":{"peak_allocated_gb":25.150440216064453,'
        '"peak_reserved_gb":29.458984375},"trace":{"gpu_busy_pct":22.637773607206874,"host_syncs_per_step":433,'
        '"kernels_per_step":18355.0},"system":{"source":"nvidia-smi --loop-ms=1000","interval_ms":1000,'
        '"during":"clean steps","samples":66,"metrics":{"gpu_util_pct":{"min":8.0,"median":30.0,"max":54.0,'
        '"mean":28.984848484848484},"mem_util_pct":{"min":1.0,"median":3.0,"max":34.0,"mean":10.242424242424242},'
        '"mem_used_mib":{"min":31007.0,"median":31009.0,"max":31011.0,"mean":31009.757575757576},'
        '"sm_clock_mhz":{"min":1980.0,"median":1980.0,"max":1980.0,"mean":1980.0},'
        '"mem_clock_mhz":{"min":3201.0,"median":3201.0,"max":3201.0,"mean":3201.0},'
        '"power_w":{"min":162.85,"median":189.79000000000002,"max":237.18,"mean":196.1695454545455},'
        '"temp_c":{"min":35.0,"median":37.0,"max":40.0,"mean":37.10606060606061}},"slowdown_samples":0,'
        '"slowdown_reasons":[]}}'
    ),
}


def resolve_source_text(source: str) -> tuple[str, str, str]:
    """Return `(canonical_source, default_run_id, text_content)` from disk or git ref."""
    p = Path(source)
    if not p.is_absolute():
        cand = REPO_ROOT / p
        if cand.exists():
            p = cand

    if p.exists() and p.is_dir():
        jsonl_cand = p / "metrics.jsonl"
        if jsonl_cand.exists():
            p = jsonl_cand

    if p.exists() and p.is_file():
        try:
            rel = str(p.resolve().relative_to(REPO_ROOT.resolve()))
        except ValueError:
            rel = str(p)
        run_id = p.parent.name if p.name == "metrics.jsonl" else p.stem
        return rel, run_id, p.read_text(encoding="utf-8")

    # Fallback: check git refs (e.g. `pr-135:<path>`, `pr-186:<path>`, or `upstream/main:<path>`).
    git_spec = source[4:] if source.startswith("git:") else source
    if git_spec.endswith("/"):
        git_spec = f"{git_spec}metrics.jsonl"
    candidates = [git_spec] if ":" in git_spec else [
        f"pr-186:{git_spec}",
        f"pr-135:{git_spec}",
        f"upstream/main:{git_spec}",
        f"HEAD:{git_spec}",
    ]
    for spec in candidates:
        res = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "show", spec],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout and not res.stdout.startswith("tree "):
            rel_path = spec.split(":", 1)[1]
            pp = Path(rel_path)
            run_id = pp.parent.name if pp.name == "metrics.jsonl" else pp.stem
            return rel_path, run_id, res.stdout

    rel_lookup = git_spec.split(":", 1)[-1].lstrip("./")
    if rel_lookup in _FALLBACK_SOURCES:
        pp = Path(rel_lookup)
        run_id = pp.parent.name if pp.name == "metrics.jsonl" else pp.stem
        return rel_lookup, run_id, _FALLBACK_SOURCES[rel_lookup]

    raise FileNotFoundError(f"Cannot find source file on disk or in git refs: {source}")


def _parse_jsonl_content(text: str, default_run_id: str, run_id_override: str | None = None) -> dict:
    raw_lines = [ln for ln in text.splitlines() if ln.strip()]
    rows: list[dict] = []
    null_rows = 0
    resolved_run_id = run_id_override or default_run_id

    for idx, line in enumerate(raw_lines):
        rec = json.loads(line)
        if not isinstance(rec, dict):
            raise ValueError(f"Line {idx + 1} is not a JSON object")

        if not run_id_override and isinstance(rec.get("run_id"), str) and rec["run_id"].strip():
            resolved_run_id = rec["run_id"].strip()

        step_raw = rec.get("step", idx)
        step = int(step_raw) if isinstance(step_raw, (int, float)) and not isinstance(step_raw, bool) else idx
        fallback_dt = EPOCH_BASE + timedelta(seconds=idx)
        dt = _parse_time(rec.get("time", rec.get("timestamp")), fallback_dt)
        time_str = _format_utc(dt)

        rank_raw = rec.get("rank", 0)
        if isinstance(rec.get("gpu"), dict) and isinstance(rec["gpu"].get("index"), int):
            rank_raw = rec["gpu"]["index"]
        rank = int(rank_raw) if isinstance(rank_raw, int) and not isinstance(rank_raw, bool) and rank_raw >= 0 else 0

        event = rec.get("event")
        # 1. Tall single-metric JSONL line: {"step": ..., "name": ..., "value": ...}
        if "name" in rec and "value" in rec and isinstance(rec["name"], str):
            val = _to_nullable_float(rec["value"])
            if val is None:
                null_rows += 1
            rows.append({
                "run_id": resolved_run_id,
                "step": step,
                "time": time_str,
                "name": rec["name"],
                "value": val,
                "rank": rank,
            })
            continue

        # 2. Team 6 live `gpu_sample` JSONL line
        if event == "gpu_sample" and isinstance(rec.get("metrics"), dict):
            m_dict = dict(rec["metrics"])
            if "gpu_util_pct" in m_dict and "gpu_utilization" not in m_dict:
                m_dict["gpu_utilization"] = m_dict["gpu_util_pct"]
            if "mem_used_mib" in m_dict and "gpu_memory_used" not in m_dict:
                mib = _to_nullable_float(m_dict["mem_used_mib"])
                m_dict["gpu_memory_used"] = mib * 1048576.0 if mib is not None else None
            for m_name, m_val in m_dict.items():
                val = _to_nullable_float(m_val)
                if val is None:
                    null_rows += 1
                rows.append({
                    "run_id": resolved_run_id,
                    "step": step,
                    "time": time_str,
                    "name": str(m_name),
                    "value": val,
                    "rank": rank,
                })
            continue

        # 3. Team 6 live `step_timing` JSONL line
        if event == "step_timing":
            for m_name in ("data_ms", "raw_step_ms"):
                if m_name in rec:
                    val = _to_nullable_float(rec[m_name])
                    if val is None:
                        null_rows += 1
                    rows.append({
                        "run_id": resolved_run_id,
                        "step": step,
                        "time": time_str,
                        "name": m_name,
                        "value": val,
                        "rank": rank,
                    })
            if "data_ms" in rec:
                dms = _to_nullable_float(rec["data_ms"])
                rows.append({
                    "run_id": resolved_run_id,
                    "step": step,
                    "time": time_str,
                    "name": "loader_wait_time",
                    "value": dms / 1000.0 if dms is not None else None,
                    "rank": rank,
                })
                if dms is None:
                    null_rows += 1
            continue

        # 4. Standard wide per-step JSONL line (Team 5 `train.py` or `MetricsWriter`)
        skip_keys = {
            "step", "time", "timestamp", "run_id", "node_id", "rank", "local_rank",
            "schema_version", "event", "mfu_unavailable_reason", "hfu_unavailable_reason",
            "mfu_method", "mfu_scope",
        }
        line_metrics = 0
        for k, v in rec.items():
            if k in skip_keys:
                continue
            if isinstance(v, (list, tuple)):
                for sub_i, sub_v in enumerate(v):
                    val = _to_nullable_float(sub_v)
                    if val is None:
                        null_rows += 1
                    rows.append({
                        "run_id": resolved_run_id,
                        "step": step,
                        "time": time_str,
                        "name": f"{k}.{sub_i}",
                        "value": val,
                        "rank": rank,
                    })
                    line_metrics += 1
            elif isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    if isinstance(sub_v, (list, tuple)):
                        for sub_i, item_v in enumerate(sub_v):
                            val = _to_nullable_float(item_v)
                            if val is None:
                                null_rows += 1
                            rows.append({
                                "run_id": resolved_run_id,
                                "step": step,
                                "time": time_str,
                                "name": f"{k}.{sub_k}.{sub_i}",
                                "value": val,
                                "rank": rank,
                            })
                            line_metrics += 1
                    else:
                        val = _to_nullable_float(sub_v)
                        if val is None:
                            null_rows += 1
                        rows.append({
                            "run_id": resolved_run_id,
                            "step": step,
                            "time": time_str,
                            "name": f"{k}.{sub_k}",
                            "value": val,
                            "rank": rank,
                        })
                        line_metrics += 1
            else:
                val = _to_nullable_float(v)
                if val is None:
                    null_rows += 1
                rows.append({
                    "run_id": resolved_run_id,
                    "step": step,
                    "time": time_str,
                    "name": str(k),
                    "value": val,
                    "rank": rank,
                })
                line_metrics += 1

        if line_metrics == 0:
            null_rows += 1
            rows.append({
                "run_id": resolved_run_id,
                "step": step,
                "time": time_str,
                "name": "_empty_line",
                "value": None,
                "rank": rank,
            })

    return {
        "run_id": resolved_run_id,
        "jsonl_lines": len(raw_lines),
        "metric_rows": len(rows),
        "null_rows": null_rows,
        "rows": rows,
    }


def _parse_team6_run_json(text: str, default_run_id: str, run_id_override: str | None = None) -> dict:
    doc = json.loads(text)
    meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
    resolved_run_id = run_id_override or meta.get("tag") or default_run_id
    base_dt = _parse_time(meta.get("time"), EPOCH_BASE)

    rows: list[dict] = []
    null_rows = 0

    def add(step: int, dt: datetime, name: str, raw_val: object, rank: int = 0) -> None:
        nonlocal null_rows
        val = _to_nullable_float(raw_val)
        if val is None:
            null_rows += 1
        rows.append({
            "run_id": resolved_run_id,
            "step": step,
            "time": _format_utc(dt),
            "name": name,
            "value": val,
            "rank": rank,
        })

    clean = doc.get("clean") if isinstance(doc.get("clean"), dict) else {}
    raw_steps = clean.get("raw_step_ms")
    if isinstance(raw_steps, dict):
        raw_steps = raw_steps.get("values")
    if not isinstance(raw_steps, list):
        raw_steps = []

    elapsed_ms = 0.0
    for s_idx, step_ms in enumerate(raw_steps):
        ms_val = _to_nullable_float(step_ms)
        if ms_val is not None and ms_val > 0:
            elapsed_ms += ms_val
        else:
            elapsed_ms += 100.0
        step_dt = base_dt + timedelta(milliseconds=elapsed_ms)
        add(s_idx, step_dt, "step_ms", step_ms)

    summary_step = max(0, len(raw_steps) - 1)
    summary_dt = base_dt + timedelta(milliseconds=elapsed_ms)

    # Summary KPIs from `metrics`
    metrics_sec = doc.get("metrics") if isinstance(doc.get("metrics"), dict) else {}
    for k in (
        "tokens_per_step", "tokens_per_s", "global_tokens_per_s", "model_flops_per_token",
        "hw_flops_per_token", "params_total", "params_active",
        "peak_tflops", "model_tflops_per_s", "mfu", "hfu",
    ):
        if k in metrics_sec:
            add(summary_step, summary_dt, k, metrics_sec[k])
    if "mfu" in metrics_sec:
        add(summary_step, summary_dt, "model_flops_utilization", metrics_sec["mfu"])
    if "tokens_per_s" in metrics_sec:
        add(summary_step, summary_dt, "tokens_per_second", metrics_sec["tokens_per_s"])
    parts = metrics_sec.get("participants")
    if isinstance(parts, dict):
        for pk in ("world_size", "peak_tflops_sum"):
            if pk in parts:
                add(summary_step, summary_dt, f"participants.{pk}", parts[pk])

    # Clean step & data wait summary stats
    for sec_name in ("step_ms", "data_ms"):
        stats = clean.get(sec_name)
        if isinstance(stats, dict):
            for stat_k in ("median", "p10", "p90", "mean", "min", "max"):
                if stat_k in stats:
                    add(summary_step, summary_dt, f"clean.{sec_name}.{stat_k}", stats[stat_k])
            if sec_name == "data_ms" and "median" in stats:
                dms = _to_nullable_float(stats["median"])
                add(summary_step, summary_dt, "loader_wait_time", dms / 1000.0 if dms is not None else None)

    # Memory stats
    mem_sec = doc.get("memory") if isinstance(doc.get("memory"), dict) else {}
    for k in ("peak_allocated_gb", "peak_reserved_gb"):
        if k in mem_sec:
            add(summary_step, summary_dt, f"memory.{k}", mem_sec[k])
    if "peak_allocated_gb" in mem_sec:
        add(summary_step, summary_dt, "gpu_alloc_gb", mem_sec["peak_allocated_gb"])

    # Trace stats
    trace_sec = doc.get("trace") if isinstance(doc.get("trace"), dict) else {}
    for k in ("gpu_busy_pct", "host_syncs_per_step", "kernels_per_step"):
        if k in trace_sec:
            add(summary_step, summary_dt, f"trace.{k}", trace_sec[k])

    # 1 Hz GPU system telemetry summary stats
    sys_sec = doc.get("system") if isinstance(doc.get("system"), dict) else {}
    sys_metrics = sys_sec.get("metrics") if isinstance(sys_sec.get("metrics"), dict) else {}
    for m_name, m_stats in sys_metrics.items():
        if isinstance(m_stats, dict):
            for stat_k in ("min", "median", "max", "mean"):
                if stat_k in m_stats:
                    add(summary_step, summary_dt, f"system.{m_name}.{stat_k}", m_stats[stat_k])
            if "median" in m_stats:
                add(summary_step, summary_dt, m_name, m_stats["median"])
                if m_name == "gpu_util_pct":
                    add(summary_step, summary_dt, "gpu_utilization", m_stats["median"])
        else:
            add(summary_step, summary_dt, m_name, m_stats)
    if "mem_used_mib" in sys_metrics and isinstance(sys_metrics["mem_used_mib"], dict):
        max_mib = _to_nullable_float(sys_metrics["mem_used_mib"].get("max"))
        add(
            summary_step,
            summary_dt,
            "gpu_memory_used",
            max_mib * 1048576.0 if max_mib is not None else None,
        )

    line_count = len(raw_steps) if raw_steps else 1
    return {
        "target_table": "metrics_raw",
        "run_id": resolved_run_id,
        "jsonl_lines": line_count,
        "metric_rows": len(rows),
        "null_rows": null_rows,
        "rows": rows,
    }


EVAL_MINI_KEY_FIELDS = (
    "model",
    "model_revision",
    "format",
    "item_set",
    "task",
    "num_fewshot",
    "metric",
    "filter",
)
EVAL_MINI_NULLABLE_FIELDS = (
    "checkpoint",
    "derived_from",
    "seed",
    "stderr",
    "dtype",
    "n_items_total",
    "profile",
)


def _is_eval_mini_record(rec: object) -> bool:
    if not isinstance(rec, dict):
        return False
    return all(k in rec for k in EVAL_MINI_KEY_FIELDS) and "value" in rec and "harness" in rec


def _parse_eval_mini_records(
    records: list[dict],
    default_run_id: str,
    run_id_override: str | None = None,
) -> dict:
    """Dedicated reader for Team 09 `eval_mini_v1.json` (`{"records": [...]}`) and `eval_mini_v1.jsonl`."""
    resolved_run_id = run_id_override or default_run_id
    rows: list[dict] = []
    null_rows = 0
    nulls_by_col = {col: 0 for col in EVAL_MINI_NULLABLE_FIELDS}
    seen_keys: set[tuple] = set()

    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            raise ValueError(f"eval_mini record {idx} is not a JSON object")

        # Validate non-null record key (Section 4) and `value`
        for k in EVAL_MINI_KEY_FIELDS:
            if rec.get(k) is None or (isinstance(rec.get(k), str) and not rec[k].strip()):
                raise ValueError(f"eval_mini record {idx} has null/empty key field {k!r}")
        val = _to_nullable_float(rec.get("value"))
        if val is None:
            raise ValueError(f"eval_mini record {idx} has null or non-finite 'value': {rec.get('value')!r}")

        rec_key = (
            str(rec["model"]),
            str(rec["model_revision"]),
            str(rec["format"]),
            str(rec["item_set"]),
            str(rec["task"]),
            int(rec["num_fewshot"]),
            str(rec["metric"]),
            str(rec["filter"]),
        )
        if rec_key in seen_keys:
            raise ValueError(f"Duplicate eval_mini record key at index {idx}: {rec_key}")
        seen_keys.add(rec_key)

        for col in EVAL_MINI_NULLABLE_FIELDS:
            if rec.get(col) is None:
                nulls_by_col[col] += 1

        # Nullable numeric `stderr`
        stderr_val = _to_nullable_float(rec.get("stderr"))
        if stderr_val is None:
            null_rows += 1

        # Nullable nested `checkpoint` object + dotted flat columns (`checkpoint.*`)
        ckpt = rec.get("checkpoint")
        if isinstance(ckpt, dict):
            ckpt_json: str | None = json.dumps(ckpt, separators=(",", ":"), sort_keys=True)
            ckpt_run = str(ckpt["run"]) if ckpt.get("run") is not None else None
            ckpt_branch = str(ckpt["branch"]) if ckpt.get("branch") is not None else None
            ckpt_step = int(ckpt["step"]) if ckpt.get("step") is not None else None
            ckpt_epoch = int(ckpt["epoch"]) if ckpt.get("epoch") is not None else None
            ckpt_tokens = int(ckpt["tokens_seen"]) if ckpt.get("tokens_seen") is not None else None
            ckpt_path = str(ckpt["path"]) if ckpt.get("path") is not None else None
        else:
            ckpt_json = None
            ckpt_run = None
            ckpt_branch = None
            ckpt_step = None
            ckpt_epoch = None
            ckpt_tokens = None
            ckpt_path = None

        # Nullable nested `seed` object + dotted flat columns (`seed.*`)
        seed_obj = rec.get("seed")
        if isinstance(seed_obj, dict):
            seed_json: str | None = json.dumps(seed_obj, separators=(",", ":"), sort_keys=True)
            seed_random = int(seed_obj["random"]) if seed_obj.get("random") is not None else None
            seed_numpy = int(seed_obj["numpy"]) if seed_obj.get("numpy") is not None else None
            seed_torch = int(seed_obj["torch"]) if seed_obj.get("torch") is not None else None
            seed_fewshot = int(seed_obj["fewshot"]) if seed_obj.get("fewshot") is not None else None
        else:
            seed_json = None
            seed_random = None
            seed_numpy = None
            seed_torch = None
            seed_fewshot = None

        # Required nested `harness` object (`{name, version}` + optional `script_sha256`)
        harness_obj = rec.get("harness") if isinstance(rec.get("harness"), dict) else {}
        harness_name = str(harness_obj.get("name") or "")
        harness_version = str(harness_obj.get("version") or "")
        harness_script_sha256 = (
            str(harness_obj["script_sha256"]) if harness_obj.get("script_sha256") is not None else None
        )

        # Nullable `derived_from` list
        df_raw = rec.get("derived_from")
        if isinstance(df_raw, list):
            derived_from_json: str | None = json.dumps([str(x) for x in df_raw], separators=(",", ":"))
        else:
            derived_from_json = None

        notes_raw = rec.get("notes")
        notes_list = [str(x) for x in notes_raw] if isinstance(notes_raw, list) else []

        n_items_total_raw = rec.get("n_items_total")
        n_items_total = int(n_items_total_raw) if n_items_total_raw is not None else None

        rows.append({
            "run_id": resolved_run_id,
            "model": str(rec["model"]),
            "model_revision": str(rec["model_revision"]),
            "format": str(rec["format"]),
            "item_set": str(rec["item_set"]),
            "task": str(rec["task"]),
            "num_fewshot": int(rec["num_fewshot"]),
            "metric": str(rec["metric"]),
            "filter": str(rec["filter"]),
            "backend": str(rec.get("backend") or ""),
            "primary": 1 if bool(rec.get("primary")) else 0,
            "value": val,
            "stderr": stderr_val,
            "dtype": str(rec["dtype"]) if rec.get("dtype") is not None else None,
            "n_items": int(rec.get("n_items") or 0),
            "n_items_total": n_items_total,
            "profile": str(rec["profile"]) if rec.get("profile") is not None else None,
            "decoding": str(rec.get("decoding") or ""),
            "checkpoint": ckpt_json,
            "checkpoint_run": ckpt_run,
            "checkpoint_branch": ckpt_branch,
            "checkpoint_step": ckpt_step,
            "checkpoint_epoch": ckpt_epoch,
            "checkpoint_tokens_seen": ckpt_tokens,
            "checkpoint_path": ckpt_path,
            "seed": seed_json,
            "seed_random": seed_random,
            "seed_numpy": seed_numpy,
            "seed_torch": seed_torch,
            "seed_fewshot": seed_fewshot,
            "harness_name": harness_name,
            "harness_version": harness_version,
            "harness_script_sha256": harness_script_sha256,
            "hardware": str(rec.get("hardware") or ""),
            "run_date": str(rec.get("run_date") or ""),
            "derived_from": derived_from_json,
            "notes": notes_list,
        })

    return {
        "target_table": "eval_mini",
        "run_id": resolved_run_id,
        "jsonl_lines": len(rows),
        "metric_rows": len(rows),
        "null_rows": null_rows,
        "nulls_by_col": nulls_by_col,
        "rows": rows,
    }


def parse_source(source: str, run_id_override: str | None = None) -> dict:
    """Parse a JSONL, Team 09 `eval_mini_v1.json`/`.jsonl`, or Team 6 JSON source into ClickHouse rows."""
    canonical_source, default_run_id, text = resolve_source_text(source)
    stripped = text.lstrip()

    # 1. Check if the source is a single JSON document (`eval_mini_v1.json` or Team 6 `.json`)
    if stripped.startswith("{"):
        try:
            doc = json.loads(stripped)
        except json.JSONDecodeError:
            doc = None
        if isinstance(doc, dict):
            if doc.get("schema_version") == "eval_mini_v1" or (
                isinstance(doc.get("records"), list)
                and (not doc["records"] or _is_eval_mini_record(doc["records"][0]))
            ):
                parsed = _parse_eval_mini_records(doc.get("records", []), default_run_id, run_id_override)
                parsed["source_file"] = canonical_source
                return parsed
            if (canonical_source.endswith(".json") and not canonical_source.endswith(".jsonl")) or (
                "clean" in doc and "meta" in doc
            ):
                parsed = _parse_team6_run_json(text, default_run_id, run_id_override)
                parsed["source_file"] = canonical_source
                return parsed

    # 2. Check if JSONL lines are `eval_mini_v1` records (from Section 2's one-line JSONL conversion)
    raw_lines = [ln for ln in text.splitlines() if ln.strip()]
    if raw_lines:
        try:
            first_obj = json.loads(raw_lines[0])
        except json.JSONDecodeError:
            first_obj = None
        if _is_eval_mini_record(first_obj):
            records = [json.loads(ln) for ln in raw_lines]
            parsed = _parse_eval_mini_records(records, default_run_id, run_id_override)
            parsed["source_file"] = canonical_source
            return parsed

    parsed = _parse_jsonl_content(text, default_run_id, run_id_override)
    parsed["target_table"] = "metrics_raw"
    parsed["source_file"] = canonical_source
    return parsed


def load_source(source: str, run_id_override: str | None = None, url: str = DEFAULT_CH_URL) -> dict:
    """Parse `source` and load its rows into ClickHouse (`metrics_raw` or `eval_mini`) and `ingest_manifest`."""
    ensure_schema(url=url)
    parsed = parse_source(source, run_id_override=run_id_override)
    target_table = parsed.get("target_table", "metrics_raw")
    run_id = parsed["run_id"]
    source_file = parsed["source_file"]
    safe_run = run_id.replace("'", "''")
    safe_src = source_file.replace("'", "''")

    # Idempotent reload: remove previous rows for this `run_id` before inserting.
    ch_Exec(
        f"ALTER TABLE {target_table} DELETE WHERE run_id = '{safe_run}' SETTINGS mutations_sync = 2",
        url=url,
    )
    ch_Exec(
        f"ALTER TABLE ingest_manifest DELETE WHERE run_id = '{safe_run}' AND source_file = '{safe_src}' SETTINGS mutations_sync = 2",
        url=url,
    )

    payload_lines = [json.dumps(r, separators=(",", ":")) for r in parsed["rows"]]
    if payload_lines:
        body = ("\n".join(payload_lines) + "\n").encode("utf-8")
        ch_Exec(f"INSERT INTO {target_table} FORMAT JSONEachRow", data=body, url=url)

    manifest_row = {
        "run_id": run_id,
        "source_file": source_file,
        "jsonl_lines": parsed["jsonl_lines"],
        "metric_rows": parsed["metric_rows"],
        "null_rows": parsed["null_rows"],
    }
    ch_Exec(
        "INSERT INTO ingest_manifest (run_id, source_file, jsonl_lines, metric_rows, null_rows) FORMAT JSONEachRow",
        data=(json.dumps(manifest_row) + "\n").encode("utf-8"),
        url=url,
    )
    return {
        "target_table": target_table,
        "run_id": run_id,
        "source_file": source_file,
        "jsonl_lines": parsed["jsonl_lines"],
        "metric_rows": parsed["metric_rows"],
        "null_rows": parsed["null_rows"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Load Team 5 JSONL and Team 6 JSON runs into ClickHouse.")
    ap.add_argument("sources", nargs="*", help="JSONL files, run directories, or Team 6 JSON files to load")
    ap.add_argument("--defaults", action="store_true", help="Load Team 5 run_a, run_b and Team 6 PR #135 h200_v1.json")
    ap.add_argument("--run-id", default=None, help="Explicit run_id override (when loading a single source)")
    ap.add_argument("--url", default=DEFAULT_CH_URL, help=f"ClickHouse HTTP URL (default: {DEFAULT_CH_URL})")
    args = ap.parse_args(argv)

    targets = list(args.sources)
    if args.defaults or not targets:
        targets.extend(DEFAULT_SOURCES)

    if args.run_id and len(targets) > 1:
        print("error: --run-id can only be used when loading a single file", file=sys.stderr)
        return 2

    for src in targets:
        info = load_source(src, run_id_override=args.run_id, url=args.url)
        print(
            f"loaded run_id={info['run_id']!r} source={info['source_file']} "
            f"lines={info['jsonl_lines']} metric_rows={info['metric_rows']} null_rows={info['null_rows']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
