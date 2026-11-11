"""Parallel download -> convert -> decontam for several SFT sets at once (G10).

    python decontam_pipeline.py --sets sft-code-opencodereasoning sft-math-openr1-math --work /data/p5 \
        --records /data/run

For each set the source files are split into units. One `convert.py` process per unit downloads and renders its
file, and writes the rows as parts of about `--roll-mb` MB. Every finished part goes straight to
`decontam_run.py` (full fingerprint set, canary scan, second pass over the clean part), so downloading, rendering
and checking overlap and the cores stay busy. A part's input and clean file are deleted once its record is
written; the record keeps their sha256. When all parts of a set are done, the part records are merged into
`<records>/<set>.record.json` (the file `decontam_report.py` reads), with extra checks that the parts cover the
whole source and that the document ids do not overlap.

Progress is written for a person to watch:
    <work>/progress.log   one line per event (unit and part start/end, set done, errors)
    <work>/status.txt     rewritten every few seconds: per set files, GB downloaded, rows, parts, flagged, ETA

No document text is printed or written outside the work folder. Run with plain `python` and
`G10_DECONTAM_TOOLS` set to Team 9's decontam folder.
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import convert  # noqa: E402
import decontam_run as dr  # noqa: E402

STRIDE = 100_000_000  # ids of unit k start at k * STRIDE, so they cannot overlap while a file has fewer rows


def hub_sizes(dataset):
    """{path: bytes} of the data files of a Hub dataset repo."""
    for attempt in range(4):
        try:
            with urllib.request.urlopen(f"https://huggingface.co/api/datasets/{dataset}/tree/main?recursive=1",
                                        timeout=60) as r:
                return {x["path"]: x.get("size", 0) for x in json.load(r) if x.get("size")}
        except OSError:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))


def plan_units(set_id, limit_units=None, from_hub=False):
    meta = convert.licence_row(set_id)
    kind, spec = convert.ADAPTERS[set_id][2]
    if kind != "file":
        raise SystemExit(f"{set_id}: only sets read from Hub files can run here (source kind '{kind}')")
    sizes = hub_sizes(meta["source"])
    if from_hub and spec.startswith("glob:"):  # files are still arriving: list them from the Hub, not from the folder
        prefix, _, suffix = spec[5:].partition("*")
        names = sorted(n for n in sizes if n.startswith(prefix) and n.endswith(suffix or (".parquet", ".jsonl")))
    else:
        names = convert.expand_paths(meta["source"], spec)
    units = [{"set": set_id, "dataset": meta["source"], "idx": i, "file": n, "bytes": sizes.get(n, 0), "base": i * STRIDE}
             for i, n in enumerate(names)]
    return units[:limit_units] if limit_units else units, len(names)


def gb(n):
    return f"{n / 1e9:,.2f}"


def local_ready(u):
    """True when the unit's file is in the local copy (G10_LOCAL_ROOT) and the downloader marked it complete (`<file>.ok`,
    written after the Hub sha256 matched). A file that is still downloading has no marker, so it is never read half-way."""
    path = convert.local_path(u["dataset"], u["file"])
    return path is not None and path.is_file() and Path(str(path) + ".ok").exists()


def delete_local_source(u):
    """Remove the unit's source file and marker once its converter has read all of it (frees the disk for the next file)."""
    path = convert.local_path(u["dataset"], u["file"])
    for f in (path, Path(str(path) + ".ok")) if path is not None else ():
        f.unlink(missing_ok=True)


class Pipeline:
    def __init__(self, a):
        self.a = a
        self.work = Path(a.work).resolve()
        self.records = Path(a.records).resolve()
        for d in ("in", "shards", "manifests", "logs", "progress"):
            (self.work / d).mkdir(parents=True, exist_ok=True)
        self.records.mkdir(parents=True, exist_ok=True)
        self.log_f = open(self.work / "progress.log", "a", encoding="utf-8", buffering=1)
        self.t0 = time.time()
        self.units, self.n_files = [], {}
        self.tasks = []  # decontam tasks
        self.seen_parts = set()
        self.ready = []
        self.failed_sets = {}
        self.merged = set()
        self.last_status = 0
        self.last_disk_msg = None
        self.dec_bytes_done = 0
        self.rendered_bytes = 0

    # --- logging -----------------------------------------------------------------------------
    def log(self, msg):
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
        self.log_f.write(line + "\n")

    def free_gb(self):
        return shutil.disk_usage(self.work).free / 1e9

    # --- planning ----------------------------------------------------------------------------
    def plan(self):
        for s in self.a.sets:
            units, n = plan_units(s, self.a.limit_units, from_hub=self.a.wait_ready)
            self.units += units
            self.n_files[s] = n
            self.log(f"plan {s}: {len(units)} units, {gb(sum(u['bytes'] for u in units))} GB of source files")
        # big files first: the longest single downloads start earliest
        self.units.sort(key=lambda u: -u["bytes"])
        for u in self.units:
            u.update(status="pending", proc=None, parts=0, manifest=None, rows=0, bytes_read=0)
        if self.a.resume:  # a unit whose converter finished (it wrote its manifest) is not converted again
            for u in self.units:
                manifest = Path(f"{self.unit_paths(u)[0]}.manifest.json")
                if manifest.is_file():
                    m = json.loads(manifest.read_text(encoding="utf-8"))
                    u.update(status="done", manifest=m, rows=m["rows"], bytes_read=u["bytes"], started=time.time(), resumed=True)
                    self.log(f"resume: unit u{u['idx']:03d} of {u['set']} was converted before ({m['rows']:,} rows, {len(m['parts'])} parts)")

    # --- units (download + render) -----------------------------------------------------------
    def unit_paths(self, u):
        d = self.work / "in" / u["set"]
        d.mkdir(parents=True, exist_ok=True)
        return d / f"u{u['idx']:03d}", self.work / "progress" / f"{u['set']}.u{u['idx']:03d}.json"

    def start_unit(self, u):
        prefix, prog = self.unit_paths(u)
        cmd = [sys.executable, str(HERE / "convert.py"), "--set", u["set"], "--hf-file", "1000000000",
               "--file-spec", u["file"], "--index-base", str(u["base"]), "--roll-mb", str(self.a.roll_mb),
               "--progress", str(prog), "--out", str(prefix)]
        if self.a.limit_rows:
            cmd += ["--limit", str(self.a.limit_rows)]
        logf = open(self.work / "logs" / f"{u['set']}.u{u['idx']:03d}.log", "w")
        u["proc"] = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT)
        u["status"], u["started"] = "running", time.time()
        self.log(f"unit start {u['set']} u{u['idx']:03d} {u['file']} ({gb(u['bytes'])} GB)")

    def read_progress(self, u):
        _, prog = self.unit_paths(u)
        try:
            d = json.loads(prog.read_text(encoding="utf-8"))
            u["rows"], u["bytes_read"] = d["rows"], d["bytes_read"]
        except (OSError, ValueError):
            pass

    def finish_unit(self, u, rc):
        prefix, _ = self.unit_paths(u)
        if rc == 0:
            try:
                u["manifest"] = json.loads(Path(f"{prefix}.manifest.json").read_text(encoding="utf-8"))
                u["status"] = "done"
                u["rows"], u["bytes_read"] = u["manifest"]["rows"], u["bytes"]
                self.log(f"unit done {u['set']} u{u['idx']:03d}: rows {u['manifest']['rows']:,} of "
                         f"{u['manifest']['rows_in']:,} selected, skipped {sum(u['manifest']['skipped'].values()):,}, "
                         f"{time.time() - u['started']:.0f}s")
                if self.a.delete_source:
                    delete_local_source(u)
                    self.log(f"source deleted {u['set']} u{u['idx']:03d} {u['file']}")
                return
            except (OSError, ValueError) as e:
                self.log(f"unit ERROR {u['set']} u{u['idx']:03d}: no manifest ({e})")
        u["status"] = "failed"
        self.failed_sets[u["set"]] = f"unit u{u['idx']:03d} failed (rc {rc}), see logs/{u['set']}.u{u['idx']:03d}.log"
        self.log(f"unit FAILED {u['set']} u{u['idx']:03d} rc {rc}")

    # --- parts (decontam) --------------------------------------------------------------------
    def _add_part(self, u, p, done=False):
        self.seen_parts.add(p)
        u["parts"] += 1
        t = {"set": u["set"], "unit": u, "part": p, "bytes": p.stat().st_size if p.exists() else 0, "proc": None,
             "id": f"{u['set']}.{p.name[:-len('.jsonl')].replace('.part', '.p')}", "status": "ready"}
        self.tasks.append(t)
        if done:  # checked before the restart: its record is already written
            r = json.loads(self.record_path(t).read_text(encoding="utf-8"))
            t["status"], t["rec"] = "done", {k: r[k] for k in ("rows_in", "rows_flagged", "rows_canary", "rows_kept")}
            p.unlink(missing_ok=True)
            self.log(f"resume: part {t['id']} was checked before (flagged {r['rows_flagged']:,}, kept {r['rows_kept']:,})")
        else:
            self.ready.append(t)
            self.rendered_bytes += t["bytes"]

    def discover_parts(self):
        for u in self.units:
            if u["status"] not in ("running", "done"):
                continue
            prefix, _ = self.unit_paths(u)
            if u.get("resumed"):  # the manifest lists the parts the converter wrote
                for name in u["manifest"]["parts"]:
                    p = prefix.parent / name
                    if p in self.seen_parts:
                        continue
                    rec = self.work / "shards" / u["set"] / f"{u['set']}.{name[:-len('.jsonl')].replace('.part', '.p')}.record.json"
                    if rec.is_file() or p.exists():
                        self._add_part(u, p, done=rec.is_file())
                    else:
                        self.failed_sets[u["set"]] = f"resume: part {name} has neither input nor record"
                        self.log(f"SET FAILED {u['set']}: part {name} has neither input nor record")
                        self.seen_parts.add(p)
                continue
            for p in sorted(prefix.parent.glob(f"{prefix.name}.part*.jsonl")):
                if p not in self.seen_parts:
                    self._add_part(u, p)

    def start_task(self, t):
        out = self.work / "shards" / t["set"]
        out.mkdir(parents=True, exist_ok=True)
        if self.a.resume:  # a part that was running when the run stopped starts over
            for stale in out.glob(f"{t['id']}.*"):
                stale.unlink(missing_ok=True)
        cmd = [sys.executable, str(HERE / "decontam_run.py"), "--set", t["id"], "--input", str(t["part"]),
               "--out-dir", str(out), "--drop-clean"]
        logf = open(self.work / "logs" / f"{t['id']}.log", "w")
        t["proc"] = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, env=dict(os.environ))
        t["status"], t["started"] = "running", time.time()
        self.log(f"part start {t['id']} ({t['bytes'] / 1e6:,.0f} MB)")

    def record_path(self, t):
        return self.work / "shards" / t["set"] / f"{t['id']}.record.json"

    def finish_task(self, t, rc):
        if rc == 0 and self.record_path(t).is_file():
            r = json.loads(self.record_path(t).read_text(encoding="utf-8"))
            t["status"], t["rec"] = "done", {k: r[k] for k in ("rows_in", "rows_flagged", "rows_canary", "rows_kept")}
            self.dec_bytes_done += t["bytes"]
            t["part"].unlink(missing_ok=True)
            self.log(f"part done {t['id']}: rows {r['rows_in']:,} flagged {r['rows_flagged']:,} canary "
                     f"{r['rows_canary']} kept {r['rows_kept']:,} {time.time() - t['started']:.0f}s")
        else:
            t["status"] = "failed"
            self.failed_sets[t["set"]] = f"part {t['id']} failed (rc {rc}), see logs/{t['id']}.log"
            self.log(f"part FAILED {t['id']} rc {rc} (canary or reconciliation failure keeps the part for inspection)")

    # --- sets --------------------------------------------------------------------------------
    def set_units(self, s):
        return [u for u in self.units if u["set"] == s]

    def set_complete(self, s):
        us = self.set_units(s)
        ts = [t for t in self.tasks if t["set"] == s]
        return (all(u["status"] == "done" for u in us) and all(t["status"] == "done" for t in ts)
                and sum(u["parts"] for u in us) == len(ts))

    def merge_set(self, s):
        us, ts = self.set_units(s), [t for t in self.tasks if t["set"] == s]
        recs = [json.loads(self.record_path(t).read_text(encoding="utf-8")) for t in ts]
        converted = sum(u["manifest"]["rows"] for u in us)
        extra = {
            "parts_cover_all_converted_rows": sum(r["rows_in"] for r in recs) == converted,
            "all_source_files_converted": len(us) == self.n_files[s] and all(u["status"] == "done" for u in us),
            "ids_disjoint_across_units": (len({u["base"] for u in us}) == len(us)
                                          and all(u["manifest"]["rows_scanned"] < STRIDE for u in us)),
        }
        man = {"set": s, "units": len(us), "files": [u["file"] for u in us],
               "rows_scanned": sum(u["manifest"]["rows_scanned"] for u in us),
               "rows_in": sum(u["manifest"]["rows_in"] for u in us), "rows": converted,
               "skipped": {}, "effort": {}, "selection": us[0]["manifest"]["selection"]}
        for u in us:
            for k, v in u["manifest"]["skipped"].items():
                man["skipped"][k] = man["skipped"].get(k, 0) + v
            for k, v in u["manifest"]["effort"].items():
                man["effort"][k] = man["effort"].get(k, 0) + v
        (self.work / "manifests" / f"{s}.manifest.json").write_text(json.dumps(man, indent=1) + "\n", encoding="utf-8")
        rec = dr.merge_records(s, recs, extra)
        (self.records / f"{s}.record.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                                                       encoding="utf-8")
        self.merged.add(s)
        bad = [k for k, v in rec["checks"].items() if not v]
        self.log(f"SET DONE {s}: parts {rec['parts']} rows {rec['rows_in']:,} flagged {rec['rows_flagged']:,} "
                 f"canary {rec['rows_canary']} removed {rec['rows_removed']:,} kept {rec['rows_kept']:,} "
                 f"{'OK' if rec['ok'] else 'FAILED: ' + ', '.join(bad or ['canary'])}")

    # --- status ------------------------------------------------------------------------------
    def status(self):
        now = time.time()
        el = now - self.t0
        load = os.getloadavg()[0]
        running_u = [u for u in self.units if u["status"] == "running"]
        running_t = [t for t in self.tasks if t["status"] == "running"]
        for u in running_u:
            self.read_progress(u)
        L = [f"{time.strftime('%Y-%m-%d %H:%M:%S')}  elapsed {el / 3600:.2f} h  load {load:.1f}/{os.cpu_count()}  "
             f"disk free {self.free_gb():.0f} GB",
             f"running: {len(running_u)} downloads/renders, {len(running_t)} decontam parts, {len(self.ready)} parts queued", ""]
        hdr = f"{'set':50s} {'files':>9s} {'GB down':>15s} {'rows conv':>10s} {'parts':>11s} {'rows checked':>12s} {'flagged':>8s}"
        L.append(hdr)
        tot_src = tot_down = 0
        for s in self.a.sets:
            us, ts = self.set_units(s), [t for t in self.tasks if t["set"] == s]
            src = sum(u["bytes"] for u in us)
            down = sum(min(u["bytes_read"], u["bytes"]) if u["status"] == "running" else
                       (u["bytes"] if u["status"] == "done" else 0) for u in us)
            tot_src, tot_down = tot_src + src, tot_down + down
            done_u = sum(u["status"] == "done" for u in us)
            done_t = [t for t in ts if t["status"] == "done"]
            mark = " MERGED" if s in self.merged else (" FAILED" if s in self.failed_sets else "")
            L.append(f"{s:50s} {done_u:>4d}/{len(us):<4d} {gb(down):>7s}/{gb(src):<7s} "
                     f"{sum(u['rows'] for u in us):>10,d} {len(done_t):>5d}/{len(ts):<5d} "
                     f"{sum(t['rec']['rows_in'] for t in done_t):>12,d} {sum(t['rec']['rows_flagged'] for t in done_t):>8,d}{mark}")
        frac_down = tot_down / tot_src if tot_src else 0
        proj = self.rendered_bytes / frac_down if frac_down > 0.02 else 0
        eta = ""
        if proj and self.dec_bytes_done > 0:
            rate = self.dec_bytes_done / el
            eta = f"{max(proj - self.dec_bytes_done, 0) / rate / 3600:.1f} h (rough: from decontam throughput so far)"
        L += ["", f"downloaded {gb(tot_down)} of {gb(tot_src)} GB source ({100 * frac_down:.0f}%); "
                  f"rendered so far {gb(self.rendered_bytes)} GB; decontam finished {gb(self.dec_bytes_done)} GB",
              f"ETA {eta or 'estimating'}"]
        for s, why in self.failed_sets.items():
            L.append(f"FAILED {s}: {why}")
        tmp = self.work / "status.txt.tmp"
        tmp.write_text("\n".join(L) + "\n", encoding="utf-8")
        tmp.replace(self.work / "status.txt")

    # --- main loop ---------------------------------------------------------------------------
    def run(self):
        self.plan()
        free = self.free_gb()
        self.log(f"start: sets {', '.join(self.a.sets)}; disk free {free:.0f} GB; "
                 f"decontam slots {self.a.dec_slots}, download slots {self.a.conv_slots}")
        if free < self.a.min_free_gb + 5:
            raise SystemExit(f"only {free:.0f} GB free, need at least {self.a.min_free_gb + 5:.0f}")
        while True:
            for u in self.units:
                if u["status"] == "running" and u["proc"].poll() is not None:
                    self.finish_unit(u, u["proc"].returncode)
            self.discover_parts()
            for t in self.tasks:
                if t["status"] == "running" and t["proc"].poll() is not None:
                    self.finish_task(t, t["proc"].returncode)
            running_t = sum(t["status"] == "running" for t in self.tasks)
            while self.ready and running_t < self.a.dec_slots:
                t = self.ready.pop(0)
                if t["set"] in self.failed_sets:
                    t["status"] = "skipped"
                    continue
                self.start_task(t)
                running_t += 1
            # downloads: base slots, more when the cores would otherwise sit idle
            running_u = sum(u["status"] == "running" for u in self.units)
            cap = self.a.conv_slots
            if not self.ready and running_t < self.a.dec_slots and os.getloadavg()[0] < os.cpu_count() - 2:
                cap = self.a.conv_slots * 2
            backlog = sum(t["bytes"] for t in self.ready) / 1e9
            if self.a.throttle:  # local sources render much faster than they are checked: hold the converters back
                free = self.free_gb()
                hold = backlog > self.a.max_backlog_gb or free < self.a.min_free_gb
                release = backlog < 0.6 * self.a.max_backlog_gb and free > self.a.min_free_gb + 10
                for u in self.units:
                    if u["status"] != "running" or u["proc"] is None or u["proc"].poll() is not None:
                        continue
                    if hold and not u.get("stopped"):
                        u["proc"].send_signal(signal.SIGSTOP)
                        u["stopped"] = True
                        self.log(f"held converter {u['set']} u{u['idx']:03d}: free {free:.0f} GB, backlog {backlog:.0f} GB")
                    elif release and u.get("stopped"):
                        u["proc"].send_signal(signal.SIGCONT)
                        u["stopped"] = False
            pending = [u for u in self.units if u["status"] == "pending" and u["set"] not in self.failed_sets]
            if self.a.wait_ready:  # files still downloading are not started
                pending = [u for u in pending if local_ready(u)]
            if pending and running_u < cap:
                free = self.free_gb()
                if free < self.a.min_free_gb or backlog > self.a.max_backlog_gb:
                    msg = f"paused downloads: free {free:.0f} GB, backlog {backlog:.0f} GB"
                    if msg != self.last_disk_msg:
                        self.log(msg)
                        self.last_disk_msg = msg
                else:
                    self.start_unit(pending[0])
                    continue
            for s in self.a.sets:
                if s not in self.merged and s not in self.failed_sets and self.set_complete(s):
                    try:
                        self.merge_set(s)
                    except (dr.RunError, OSError, ValueError, KeyError) as e:
                        self.failed_sets[s] = f"merge failed: {e}"
                        self.log(f"SET FAILED {s}: merge failed: {e}")
            if time.time() - self.last_status >= 5:
                self.status()
                self.last_status = time.time()
            busy = (any(u["status"] == "running" for u in self.units) or any(t["status"] == "running" for t in self.tasks)
                    or self.ready or any(u["status"] == "pending" and u["set"] not in self.failed_sets for u in self.units))  # not-ready files count as busy
            if not busy:
                break
            time.sleep(1)
        self.status()
        ok = all(s in self.merged for s in self.a.sets)
        self.log("finished: " + ("all sets merged" if ok else f"not merged: {[s for s in self.a.sets if s not in self.merged]}"))
        return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sets", nargs="+", required=True)
    ap.add_argument("--work", required=True, help="scratch folder: inputs, part records, logs, status (keep out of Git)")
    ap.add_argument("--records", required=True, help="where the merged <set>.record.json files go")
    ap.add_argument("--dec-slots", type=int, default=16, help="decontam parts run at once (one core each)")
    ap.add_argument("--conv-slots", type=int, default=6, help="download+render processes at once (doubled when cores idle)")
    ap.add_argument("--roll-mb", type=float, default=300, help="size of one part handed to the checker")
    ap.add_argument("--min-free-gb", type=float, default=20, help="stop starting downloads below this free space")
    ap.add_argument("--throttle", action="store_true", help="pause running converters while the backlog or disk limit is hit (local sources)")
    ap.add_argument("--max-backlog-gb", type=float, default=25, help="stop starting downloads when this much is queued")
    ap.add_argument("--wait-ready", action="store_true",
                    help="start a file only when the downloader has marked it complete (`<file>.ok`); lets the run start while the download is going")
    ap.add_argument("--resume", action="store_true",
                    help="continue a stopped run in the same --work folder: converted files and checked parts are not redone")
    ap.add_argument("--delete-source", action="store_true", help="delete a local source file once its converter has read all of it")
    ap.add_argument("--limit-units", type=int, help="TEST: only the first N files of each set")
    ap.add_argument("--limit-rows", type=int, help="TEST: only this many selected rows per file")
    a = ap.parse_args(argv)
    return Pipeline(a).run()


if __name__ == "__main__":
    sys.exit(main())
