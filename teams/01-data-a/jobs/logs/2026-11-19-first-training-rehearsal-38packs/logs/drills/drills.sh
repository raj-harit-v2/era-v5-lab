#!/bin/bash
# Shard-stage drills on the finished rehearsal-3pack run. Each drill writes only under out/drills/.
set -u
cd /workspace/era-v5-lab
PY=/workspace/venv/bin/python
R=out/pipeline/rehearsal-3pack
TOK=/workspace/data/tokenizers/p1536-sample-v0/tokenizer.json
PT=out/rehearsal/pack_table.json
D=out/drills
rm -rf $D; mkdir -p $D
SHARDS="$PY -I teams/01-data-a/shards/run_shards.py --input $R/final --manifest $R/pipeline_manifest.json --tokenizer $TOK --dataset-version rehearsal-p1536 --pack-table $PT"
VERIFY="$PY -I teams/01-data-a/shards/verify_shards.py --manifest $R/pipeline_manifest.json --tokenizer $TOK --pack-table $PT --out"
CHECK="$PY -I out/rehearsal/check_shard_pr60.py --expect-tokenizer p1536 --expect-dataset-version rehearsal-p1536 --specials-from $TOK"

echo "=== A. rollover: the main run's shards"
$PY - <<EOF
import json
s=json.load(open("$R/shards/shards_summary.json"))
for name,e in sorted(s["parts"].items()):
    print(f'{e["status"]:13} {name}: {len(e.get("shards",[]))} shards, docs {e.get("docs")}, tokens {e.get("tokens")}')
EOF
$CHECK $R/shards --json $D/A_check.json > $D/A_check.txt 2>&1; echo "A check_shard exit=$?"; tail -n 5 $D/A_check.txt
$VERIFY $R/shards > $D/A_verify.txt 2>&1; echo "A verify_shards exit=$?"; tail -n 3 $D/A_verify.txt

echo "=== B. interrupted shard stage, then rerun"
$SHARDS --out $D/B_int --tokens 1048576 > $D/B_run1.txt 2>&1 &
PID=$!
for i in $(seq 1 600); do n=$(ls $D/B_int/*.bin 2>/dev/null | wc -l); [ "$n" -ge 3 ] && break; kill -0 $PID 2>/dev/null || break; sleep 0.2; done
kill -9 $PID 2>/dev/null && echo "B killed run 1 (kill -9) with $(ls $D/B_int/*.bin 2>/dev/null | wc -l) .bin files on disk" || echo "B run 1 ended before the kill"
wait $PID 2>/dev/null; echo "B run 1 exit=$?"
ls -la $D/B_int | head -n 30 > $D/B_after_kill.txt
$SHARDS --out $D/B_int --tokens 1048576 > $D/B_run2.txt 2>&1; echo "B run 2 (rerun) exit=$?"; tail -n 8 $D/B_run2.txt
$VERIFY $D/B_int > $D/B_verify.txt 2>&1; echo "B verify_shards exit=$?"; tail -n 3 $D/B_verify.txt
$PY - <<EOF
import hashlib,os
a="$R/shards"; b="$D/B_int"
def h(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
fa={f for f in os.listdir(a) if f.endswith(('.bin','.idx.npy','.docs.parquet'))}
fb={f for f in os.listdir(b) if f.endswith(('.bin','.idx.npy','.docs.parquet'))}
print("B same shard files as the main run:", fa==fb, len(fa), len(fb))
diff=[f for f in sorted(fa&fb) if h(os.path.join(a,f))!=h(os.path.join(b,f))]
print("B token/index/docs files that differ from the uninterrupted run:", diff or "none")
left=[f for f in os.listdir(b) if any(x in f for x in ('.partial','.tmp','.lock'))]
print("B leftovers (.partial/.tmp/.lock):", left or "none")
EOF

echo "=== C. damaged shards"
first=$(ls $R/shards/*.bin | head -n 1); base=$(basename $first .bin)
second=$(ls $R/shards/*.bin | sed -n 2p); base2=$(basename $second .bin)
third=$(ls $R/shards/*.bin | sed -n 3p); base3=$(basename $third .bin)
for c in C1 C2 C3; do cp -r $R/shards $D/$c; done
$PY - <<EOF
p="$D/C1/$base.bin"; b=bytearray(open(p,'rb').read()); i=len(b)//2; b[i]^=0xFF; open(p,'wb').write(b)
print("C1: flipped one byte in", "$base.bin", "at", i)
EOF
truncate -s -8 $D/C2/$base2.idx.npy; echo "C2: cut 8 bytes off $base2.idx.npy"
rm $D/C3/$base3.docs.parquet; echo "C3: deleted $base3.docs.parquet"
for c in C1 C2 C3; do
  $VERIFY $D/$c > $D/${c}_verify.txt 2>&1; echo "$c verify_shards exit=$? :: $(grep -v '^ok' $D/${c}_verify.txt | head -n 2 | cut -c1-220)"
  $CHECK $D/$c > $D/${c}_check.txt 2>&1; echo "$c check_shard exit=$? :: $(grep -i -E 'fail|error' $D/${c}_check.txt | head -n 2 | cut -c1-220)"
done

echo "=== D. every document left out (token limit below every document)"
$SHARDS --out $D/D_allout --pack ind-bn-sangraha-v --tokens 16 > $D/D_run.txt 2>&1; echo "D run exit=$?"; tail -n 4 $D/D_run.txt
$PY - <<EOF
import json,os
p="$D/D_allout/shards_summary.json"
if os.path.exists(p):
    s=json.load(open(p))
    for n,e in s["parts"].items(): print("D", e["status"], n, "rows_read", e.get("rows_read"), "left_out", len(e.get("left_out",[])) if isinstance(e.get("left_out"),list) else e.get("left_out"))
    print("D .bin files written:", len([f for f in os.listdir("$D/D_allout") if f.endswith('.bin')]))
EOF
echo DRILLS_DONE
