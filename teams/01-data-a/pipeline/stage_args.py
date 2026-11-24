"""How run_pipeline.py hands paths to the four stage scripts it can run (clean, overlap, H3, dedup).

A stage's folders are decided once, in the run config, and never typed again: a stage reads the previous stage's folder and
writes its own. This module turns that into the command each script needs. All four scripts read their paths from a JSON
config, so each gets a copy of its settings file at <cfg_dir>/<stage>.json with the path keys filled in (repo-relative, as the
scripts require), and is run with --config on that copy:
  clean     input_root = the stage's "input", output_root = <clean folder>, and the input set's description from the stage:
            manifest (default: sample_manifest.json in the input folder), manifest_sha256, expected_parts, sample.
            clean_job.py also takes one --only <part> per part of the stage's "only" list (a trial on some parts)
  overlap   inputs = <clean folder>, out = <overlap folder>
  h3        inputs = <clean folder>, out = <h3 folder>, cache = <run>/h3_cache
  dedup     results = <overlap folder>, inputs = <clean folder>, out = <dedup folder>
            and, when H3 is configured, h3.matches = <h3 folder>/h3_matches.csv with remove: false

The settings file holds settings only (k, floor, pack order, pins); it is never edited. Its sha256 and the generated copy's are
returned so the manifest can record them, and a "settings_sha256" in the stage's run config is checked when present.

"script" in the stage's run config replaces the default script. It may also be a list: the script, then the arguments
that go before --config. That is how a script that is run through a wrapper is named, e.g. a cleaner run through
spec_v1_1/use_clean.py:
  "script": ["teams/01-data-a/spec_v1_1/use_clean.py", "<the tool to run>"]
The default clean script is pipeline/clean_job.py. Its settings file (pipeline/clean.json) names the cleaner ("clean", e.g.
spec_v1_1/clean.py) and pins its sha256; the job loads that file, so no wrapper is needed.

"resume": true in stages.clean continues an interrupted clean job in its own folder (the job keeps the parts it finished and
verifies them); it is written into the generated config for the job to read, and no other stage has it.

"workers": N in stages.clean is how many parts the clean job cleans at once. It replaces "workers" of the settings file in the
generated config; without it the settings file's value stands (the job's default is 1).

  build("overlap", spec, folders=..., cfg_dir=..., repo=...) -> {"command", "settings", "settings_sha256", "config", "config_sha256"}
"""
import hashlib
import json
from pathlib import Path

import clean_manifest

DEFAULT_SCRIPT = {"clean": "teams/01-data-a/pipeline/clean_job.py",
                  "overlap": "teams/01-data-a/dedup/overlap.py",
                  "h3": "teams/01-data-a/dedup/h3.py",
                  "dedup": "teams/01-data-a/dedup/dedup.py"}
STAGES = {  # {config key: the stage whose folder it names}
    "clean": {"keys": {"output_root": "clean"}},
    "overlap": {"keys": {"inputs": "clean", "out": "overlap"}},
    "h3": {"keys": {"inputs": "clean", "out": "h3"}},
    "dedup": {"keys": {"results": "overlap", "inputs": "clean", "out": "dedup"}},
}


# Settings a partial run (--only: some parts of the sample) has to change in a generated config: overlap.py would otherwise
# stop because the packs of the whole sample are missing.
PARTIAL = {"overlap": {"expected_packs": []}}


PATH_KEYS = ("input_root", "manifest", "inputs", "results", "out", "output_root")  # the generated keys that name a file or folder


class ConfigError(Exception):
    """The run config cannot be turned into a command: the message says which stage and why."""


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(folder, repo):
    """The folder as a repo-relative POSIX path, which overlap.py and dedup.py require (they reject absolute paths)."""
    try:
        return Path(folder).resolve().relative_to(Path(repo).resolve()).as_posix()
    except ValueError:
        raise ConfigError(f"{folder} is outside the repository {repo}")


def under_out(folder, repo, stage):
    """The stage scripts only write below <repo>/out (and clean needs a named subfolder of it)."""
    out = (Path(repo) / "out").resolve()
    f = Path(folder).resolve()
    if f == out or not f.is_relative_to(out):
        raise ConfigError(f"{stage}: its output {folder} must be a named subfolder of {out}: the {stage} script writes only there")


def manifest_path(spec):
    """Where clean reads the sample manifest: stages.clean.manifest, else sample_manifest.json in the input folder."""
    return str(spec.get("manifest") or (Path(spec["input"]) / "sample_manifest.json").as_posix())


def check_manifest(spec, repo):
    """The sample manifest is there, is the pinned file and describes a consistent input set: clean_manifest.validate, the
    same check the clean job runs when it starts. --plan runs it too."""
    p = Path(manifest_path(spec))
    p = p if p.is_absolute() else Path(repo) / p
    try:
        clean_manifest.validate(p, spec["manifest_sha256"], spec["expected_parts"])
    except clean_manifest.ManifestError as exc:
        hint = (" (without stages.clean.manifest it is sample_manifest.json in the input folder)"
                if not p.is_file() and not spec.get("manifest") else "")
        raise ConfigError(f"stages.clean: {exc}{hint}") from None


def generated_values(stage, folders, repo, spec=None):
    """The keys a generated config gets from the run config: {key: repo-relative folder}; for clean also the raw sample as
    input_root and the input set's description (manifest, manifest_sha256, expected_parts, sample)."""
    values = {}
    if stage == "clean" and (spec or {}).get("input"):  # build() requires it
        values = {"input_root": str(spec["input"]), "manifest": manifest_path(spec), "manifest_sha256": spec["manifest_sha256"],
                  "expected_parts": spec["expected_parts"], **({"sample": spec["sample"]} if spec.get("sample") else {})}
    if stage == "clean" and (spec or {}).get("resume") is True:
        values["resume"] = True
    if stage == "clean" and (spec or {}).get("workers") is not None:  # replaces "workers" of the settings file
        values["workers"] = spec["workers"]
    values.update({key: relative(folders[owner], repo) for key, owner in STAGES[stage]["keys"].items()})
    if stage == "h3":
        values["cache"] = relative(folders["h3"].parent / "h3_cache", repo)
    if stage == "dedup":
        values["h3"] = ({"matches": relative(folders["h3"] / "h3_matches.csv", repo),
                         "remove": False, "parallel_packs": []} if "h3" in folders else None)
    return values


def generated_config(stage, settings, folders, cfg_dir, repo, write=True, extra=None, spec=None):
    """<cfg_dir>/<stage>.json: the settings with the path keys filled in from `folders`. Written unless write=False
    (a plan or a check of the run config). Returns its path."""
    data = {**json.loads(Path(settings).read_text(encoding="utf-8")), **(extra or {}), **generated_values(stage, folders, repo, spec)}
    path = Path(cfg_dir) / f"{stage}.json"
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def build(stage, spec, folders, cfg_dir, repo, write=True, only=()):
    """The command for a run-mode stage from its run-config entry `spec` ("settings", optional "script", "input",
    "settings_sha256"), the stage folders {"clean", "overlap", "dedup"} (absolute) and where generated configs go.
    write=False checks everything and names the generated config without writing it (its config_sha256 is then None).
    only: sample parts for a trial run (clean gets one --only per part; overlap's generated config gets PARTIAL)."""
    if stage not in STAGES:
        raise ConfigError(f"{stage}: no script of the runner takes paths this way; give an explicit stages.{stage}.command")
    if not spec.get("settings"):
        raise ConfigError(f"stages.{stage}.settings (the settings file) is missing; or give an explicit stages.{stage}.command")
    settings = Path(spec["settings"])
    settings = settings if settings.is_absolute() else Path(repo) / settings
    if not settings.is_file():
        raise ConfigError(f"stages.{stage}.settings {spec['settings']} not found")
    settings_sha = sha256(settings)
    if spec.get("settings_sha256") and spec["settings_sha256"] != settings_sha:
        raise ConfigError(f"stages.{stage}.settings {spec['settings']} has sha256 {settings_sha[:12]}…, the run config pins "
                          f"{spec['settings_sha256'][:12]}…")
    script = spec.get("script", DEFAULT_SCRIPT[stage])
    script = [script] if isinstance(script, str) else script  # a list: the script, then the arguments before --config
    if not isinstance(script, list) or not script or not all(isinstance(s, str) and s for s in script):
        raise ConfigError(f"stages.{stage}.script must be a script's path, or a list of the script and the arguments that go "
                          "before --config")
    under_out(folders[stage], repo, stage)
    if "resume" in spec:
        if stage != "clean":
            raise ConfigError(f"stages.{stage}.resume: only the clean job can be resumed")
        if not isinstance(spec["resume"], bool):
            raise ConfigError(f"stages.clean.resume is {spec['resume']!r}, expected true or false")
    if stage == "clean":
        for key, what in (("input", "the folder with the raw sample parts"), ("manifest_sha256", "the pin of the sample manifest"),
                          ("expected_parts", "the part counts per split")):
            if not spec.get(key):
                raise ConfigError(f"stages.clean.{key} ({what}) is missing: it describes the input set, which the settings file does not")
        check_manifest(spec, repo)
    config =generated_config(stage, settings, folders, cfg_dir, repo, write, PARTIAL.get(stage) if only else None, spec)
    command = [*script, "--config", config.as_posix()]  # / on every OS, like the "config" field
    if stage == "clean":
        for part in only:
            command += ["--only", part]
    return {"command": command, "settings": spec["settings"], "settings_sha256": settings_sha,
            "config": config.as_posix(), "config_sha256": sha256(config) if write else None}
