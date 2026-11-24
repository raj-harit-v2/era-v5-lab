"""Validation tests for the read-only public Grafana dashboard (`grafana/public_v1.json`)."""
from __future__ import annotations

import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PUBLIC_JSON = HERE / "public_v1.json"

FORBIDDEN_INTERNAL_METRICS = (
    "gpu_power",
    "gpu_temp_c",
    "gpu_thermal_throttle",
    "gpu_memory_used",
    "gpu_alloc_gib",
    "loader_wait_time",
    "node_health",
    "gpu_telemetry_1s",
)


def _load():
    return json.loads(PUBLIC_JSON.read_text(encoding="utf-8"))


def test_public_dashboard_is_readonly_and_distinct_uid():
    d = _load()
    assert d["editable"] is False, "public dashboard must be strictly read-only (editable: false)"
    assert d["uid"] == "era-v5-public-v1"
    assert "public" in d.get("tags", [])


def test_public_dashboard_panel_ids_unique_and_non_overlapping_queries_safe():
    d = _load()
    panels = d["panels"]
    ids = [p["id"] for p in panels]
    assert len(ids) == len(set(ids)), f"duplicate panel IDs: {ids}"

    chart_panels = [p for p in panels if p["type"] != "row"]
    assert len(chart_panels) >= 6

    for p in chart_panels:
        assert p["type"] == "trend"
        # Trend panels must enforce step X-axis
        assert p.get("options", {}).get("xField") == "step"
        targets = p.get("targets", [])
        assert targets, f"panel {p['id']} has no SQL targets"
        for t in targets:
            sql = t.get("rawSql", "")
            assert sql.strip(), f"panel {p['id']} has empty rawSql"
            for forbidden in FORBIDDEN_INTERNAL_METRICS:
                assert forbidden not in sql, f"panel {p['id']} leaks internal metric/table {forbidden}"


def test_public_descriptions_name_teams_only_no_handles():
    d = _load()
    texts = [d.get("title", ""), d.get("description", "")]
    for p in d["panels"]:
        texts.append(p.get("title", ""))
        texts.append(p.get("description", ""))
    blob = "\n".join(texts)
    assert re.search(r"@[A-Za-z0-9_-]+", blob) is None, "public dashboard text must not contain @handles"


# Team 11 Release's approved sentences, one per public panel (TSAI approved in #598).
DASHBOARD_TEXT = HERE.parents[1] / "11-release" / "dashboard" / "dashboard_text.md"


def _approved_sentences():
    rows = re.findall(r"^\|\s*(.+?)\s*\|\s*(This panel .+?)\s*\|\s*$", DASHBOARD_TEXT.read_text(encoding="utf-8"), re.M)
    return dict(rows)


def test_panel_descriptions_are_team11_approved_sentences():
    approved = _approved_sentences()
    charts = [p for p in _load()["panels"] if p["type"] != "row"]
    assert {p["title"] for p in charts} == set(approved), "public panel titles must match dashboard_text.md"
    for p in charts:
        assert p["description"] == approved[p["title"]], f"panel {p['id']} text differs from dashboard_text.md"


def test_no_placeholder_text_or_dashes():
    d = _load()
    texts = [d.get("title", ""), d.get("description", "")]
    texts += [t for p in d["panels"] for t in (p.get("title", ""), p.get("description", ""))]
    for t in texts:
        assert "to be confirmed" not in t.lower(), t
        assert "—" not in t and "–" not in t, f"no em or en dash in public text: {t!r}"


def test_times_shown_in_ist():
    assert _load()["timezone"] == "Asia/Kolkata"


def test_training_pace_queries_cover_harness_and_public_names():
    panels = {p["title"]: p for p in _load()["panels"]}
    for title, names, unit in (
        ("Training Pace: Tokens per Second", ("tokens_per_second", "tokens_per_s"), "short"),
        ("Training Pace: Step Time", ("perf/step_ms", "step_time_ms"), "ms"),
    ):
        panel = panels[title]
        sql = panel["targets"][0]["rawSql"]
        assert all("'" + name + "'" in sql for name in names)
        assert "run_id IN ($run)" in sql and "value IS NOT NULL" in sql
        assert panel["fieldConfig"]["defaults"]["unit"] == unit
        step = next(o for o in panel["fieldConfig"]["overrides"] if o["matcher"]["options"] == "step")
        props = {p["id"]: p["value"] for p in step["properties"]}
        assert props == {"unit": "short", "custom.axisLabel": "step"}
