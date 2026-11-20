"""Benign isolation probe for rl-data/stdio_check.py G10_STDIO_RUNNER=local (TEST HARNESS ONLY; never training data).
Runs as root in the Modal container like the trainer. Writes a fake 'expected answers' file the way run_pilot stores
tasks (0600 file under 0700 folders) and checks that sandboxed programs cannot reach it or anything else private."""
import json, os, sys, threading, time
from pathlib import Path

def main(team: str, secret_dir: str) -> dict:
    os.environ["G10_STDIO_RUNNER"] = "local"
    sys.path.insert(0, f"{team}/rl-data")
    import stdio_check as sc
    res = {"isolation_available": sc.isolation_available(), "uid": os.getuid(), "euid": os.geteuid(),
           "platform": sys.platform}
    sd = Path(secret_dir); sd.mkdir(parents=True, exist_ok=True)
    os.chmod("/vol/runs", 0o700); os.chmod(sd.parent, 0o700); os.chmod(sd, 0o700)  # as run_pilot does
    fake = sd / "tasks.jsonl"; fake.write_text("FAKE-EXPECTED-42\n"); os.chmod(fake, 0o600)
    os.environ["G10_STDIO_SECRET_PATHS"] = str(fake)  # stdio_check.preflight_isolation checks a sandbox uid cannot read it
    task = {"id": "probe", "time_limit_s": 4, "tests": [{"input": "1 2\n", "output": "3\n"}]}
    sc_ = lambda code: sc.score(task, f"```python\n{code}\n```")
    res["valid_reference"] = sc_("a, b = map(int, input().split())\nprint(a + b)")
    res["wrong_solution"] = sc_("a, b = map(int, input().split())\nprint(a - b)")
    # a program that tries to print the fake expected file (would score 1 if it could read it: expected "3")
    fake.write_text("3\n")
    res["read_expected_file"] = sc_(f"print(open({str(fake)!r}).read().strip())")
    fake.write_text("FAKE-EXPECTED-42\n")
    probe = f'''
import os, json, socket, signal
r = {{"uid": os.getuid(), "euid": os.geteuid(), "gid": os.getgid(), "groups": os.getgroups(), "cwd": os.getcwd()}}
def tryit(name, fn):
    try: r[name] = "ALLOWED: " + str(fn())[:80]
    except Exception as e: r[name] = "denied: " + type(e).__name__
tryit("read_fake_answers", lambda: open({str(fake)!r}).read())
tryit("list_secret_dir", lambda: os.listdir({str(sd)!r}))
tryit("list_vol_runs", lambda: os.listdir("/vol/runs"))
tryit("read_parent_environ", lambda: open(f"/proc/{{os.getppid()}}/environ", "rb").read(20))
tryit("read_parent_mem_maps", lambda: open(f"/proc/{{os.getppid()}}/maps").read(20))
tryit("read_pid1_environ", lambda: open("/proc/1/environ", "rb").read(20))
tryit("list_parent_fds", lambda: os.listdir(f"/proc/{{os.getppid()}}/fd"))
tryit("list_sandbox_base", lambda: os.listdir("/tmp/g10sbx"))
tryit("read_root_home", lambda: os.listdir("/root"))
tryit("read_team_code", lambda: os.listdir("/root/team"))
tryit("setuid_0", lambda: os.setuid(0))
tryit("kill_parent", lambda: os.kill(os.getppid(), 0))
tryit("write_tmp_outside", lambda: open("/tmp/g10_probe_written", "w").write("x"))
tryit("network_connect", lambda: socket.create_connection(("1.1.1.1", 53), timeout=3))
print(json.dumps(r))
'''
    out = sc.run_program(probe, ["\n"], 10)
    res["probe"] = json.loads(out[0]["stdout"]) if isinstance(out, list) and out and out[0]["stdout"] else out
    res["probe_wrote_tmp_visible_to_root"] = os.path.exists("/tmp/g10_probe_written")
    # cross-run: A keeps a marker in its own folder while B looks for it
    seen = {}
    def run_a():
        seen["a"] = sc.run_program("import time\nopen('marker','w').write('A-SECRET')\ntime.sleep(4)\nprint('a')",
                                   ["\n"], 10)
    th = threading.Thread(target=run_a); th.start(); time.sleep(1.5)
    b = sc.run_program("import os, glob, json\nr={}\n"
                       "try: r['glob']=glob.glob('/tmp/g10sbx/*/marker')\nexcept Exception as e: r['glob']=str(type(e))\n"
                       "found=[]\nfor d in range(61000,65000):\n    pass\n"
                       "import pathlib\nfor p in ['/tmp/g10sbx']:\n    try: r['ls']=os.listdir(p)\n    except Exception as e: r['ls']='denied: '+type(e).__name__\n"
                       "print(json.dumps(r))", ["\n"], 10)
    th.join()
    res["cross_run_a"] = seen.get("a"); res["cross_run_b"] = json.loads(b[0]["stdout"]) if isinstance(b, list) and b else b
    # leftover background process: it must not survive the run
    sc.run_program("import os, time\nif os.fork() == 0:\n    os.setsid(); time.sleep(30)\nprint('parent')", ["\n"], 5)
    import subprocess
    ps = subprocess.run(["sh", "-c", "ls /proc | grep -E '^[0-9]+$' | while read p; do stat -c %u /proc/$p 2>/dev/null; done"],
                        capture_output=True, text=True).stdout.split()
    res["sandbox_uid_processes_left"] = sum(1 for u in ps if u.isdigit() and 61000 <= int(u) < 65000)
    return res
