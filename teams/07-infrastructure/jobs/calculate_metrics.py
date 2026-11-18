import glob
import json
import os
import re
import statistics as st

for f in sorted(glob.glob("out/*/metrics.jsonl")):
    r = [json.loads(l) for l in open(f)]
    r = [x for x in r if x.get("step", 0) > 10 and x.get("perf/step_ms")]
    if not r:
        d = os.path.dirname(f)
        log = "".join(open(p, errors="ignore").read() for p in glob.glob(d + "/*.log"))
        oom = re.search(r"out of memory|OutOfMemoryError|\bOOM\b|CUDA error", log, re.I)
        print(f, "NO TRAINING METRICS:", "OOM detected in log" if oom else "likely OOM or crash (no log evidence)")
        continue
    t = sorted(x["tokens_per_second"] for x in r)
    print(f, "tok/s median %.0f  p10 %.0f  p90 %.0f" % (st.median(t), t[len(t)//10], t[9*len(t)//10]),
            " gpu_alloc_gb %.2f" % st.median(x["gpu_alloc_gb"] for x in r))
os.system("nvidia-smi --query-gpu=name,memory.total --format=csv")
