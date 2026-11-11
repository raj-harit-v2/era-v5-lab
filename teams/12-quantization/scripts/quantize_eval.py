#!/usr/bin/env python3
"""G12 week 1: bf16 baseline + llama.cpp quantization ladder + eval, one command.

    python teams/12-quantization/scripts/quantize_eval.py --eval <eval_mini_v0.json>

Steps (each one is skipped when its output already exists, so a rerun resumes):
  1. download the HF checkpoint (plain HTTPS, pinned revision)
  2. convert it to a bf16 GGUF with llama.cpp's convert_hf_to_gguf.py, at the same llama.cpp
     build as the installed binaries (a private Python 3.12 venv is made for this step only)
  3. quantize to each format; router gates (ffn_gate_inp) are never quantized by llama.cpp
     and the output layer is forced to Q8_0; both are checked in the GGUF and written to runs.csv.
     Each GGUF's SHA-256 is written to runs/manifest_<date>.json (same folder as runs.csv)
  4. serve each GGUF with llama-server, run the eval, append one row per format to runs.csv

Needs: llama.cpp binaries on PATH (brew install llama.cpp) or --llama-bin, and uv or python3.12.
Big files live in --work (default ~/.cache/era-v5-quant), never in the repo.
Disk: about 14 GB HF + 14 GB bf16 GGUF + 28 GB for the six quants (use --delete-hf / --cleanup to save space).
"""
import argparse, csv, datetime, hashlib, json, os, platform, random, re, shutil, signal, socket, subprocess, sys, time
import urllib.parse, urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNS = REPO_ROOT / 'teams/12-quantization/runs/runs.csv'
DEFAULT_FORMATS = 'bf16,Q8_0,Q6_K,Q5_K_M,Q4_K_M,Q3_K_M,Q2_K'
RUN_FIELDS = ['date', 'model', 'revision', 'format', 'bpw', 'size_gb', 'router_type', 'output_type', 'eval_set',
              'n_items', 'score', 'score_by_kind', 'quant_time_s', 'eval_time_s', 'gen_tok_s', 'machine', 'runtime', 'notes']


def log(*a):
    print(f'[{datetime.datetime.now():%H:%M:%S}]', *a, flush=True)


def run(cmd, **kw):
    log('$', ' '.join(map(str, cmd)))
    subprocess.run(list(map(str, cmd)), check=True, **kw)


def file_sha256(path):
    """SHA-256 of a GGUF. Chunked so a 14 GB baseline is not read into memory."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(16 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def record_manifest(runs_csv, gguf, fmt, model, revision):
    """Add this output file's SHA-256 to runs/manifest_<date>.json. A same-day rerun replaces that file's entry."""
    day = datetime.date.today().isoformat()
    path = Path(runs_csv).expanduser().parent / f'manifest_{day}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = json.loads(path.read_text()) if path.exists() else {}
    files = doc.setdefault('files', {})
    digest = file_sha256(gguf)
    files[gguf.name] = dict(format=fmt, model=model, revision=revision, sha256=digest, size_bytes=gguf.stat().st_size)
    doc['date'] = day
    tmp = path.with_suffix('.json.part')
    tmp.write_text(json.dumps(doc, indent=2, sort_keys=True) + '\n')
    tmp.replace(path)
    log(f'{fmt}: sha256 {digest} -> {path.name}')
    return path


# ---------------------------------------------------------------- environment
def find_bin(name, bindir):
    p = Path(bindir) / name if bindir else shutil.which(name)
    if not p or not Path(p).exists():
        sys.exit(f'{name} not found. Install llama.cpp (brew install llama.cpp) or pass --llama-bin.')
    return str(p)


def llama_build(cli):
    out = subprocess.run([cli, '--version'], capture_output=True, text=True)
    text = out.stdout + out.stderr
    # 'version: 0.7.0 (build 11669, commit 620d2225c)' (0.7+, e.g. Homebrew) or 'version: 10050 (b15ca938a)' (older)
    m = re.search(r'build (\d+), commit (\w+)', text) or re.search(r'version: (\d+) \((\w+)\)', text)
    if not m: sys.exit(f'cannot read the llama.cpp version from: {text.strip()[:200]!r}')
    return int(m.group(1)), m.group(2)


def llama_tag(build, commit):
    """llama.cpp tag of the binaries' commit. Release builds are tagged b<build>; a source build from a
    shallow clone reports build 1, so the tag is found by commit (v0.7.0 and b11669 are the same commit)."""
    out = subprocess.run(['git', 'ls-remote', '--tags', 'https://github.com/ggml-org/llama.cpp'],
                         capture_output=True, text=True, check=True).stdout
    tags = {ref.removeprefix('refs/tags/').removesuffix('^{}') for sha, ref in (l.split('\t') for l in out.splitlines())
            if sha.startswith(commit)}
    if f'b{build}' in tags: return f'b{build}'
    if tags: return sorted(tags)[0]
    sys.exit(f'no llama.cpp tag for commit {commit}: build llama.cpp from a tagged release')


def machine_string():
    if platform.system() == 'Darwin':
        sc = lambda k: subprocess.run(['sysctl', '-n', k], capture_output=True, text=True).stdout.strip()
        gb = int(sc('hw.memsize')) // 2**30
        return f'{sc("machdep.cpu.brand_string")} {gb}GB, macOS {platform.mac_ver()[0]}, Metal'
    gpu = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                         capture_output=True, text=True).stdout.strip().replace('\n', ' + ') if shutil.which('nvidia-smi') else ''
    return f'{platform.processor() or platform.machine()}, {platform.system()} {platform.release()}' + (f', {gpu}' if gpu else ', CPU')


# ---------------------------------------------------------------- 1. download
def hf_download(model, revision, dest):
    dest.mkdir(parents=True, exist_ok=True)
    api = f'https://huggingface.co/api/models/{model}/revision/{revision}'
    info = json.load(urllib.request.urlopen(api))
    files = [s['rfilename'] for s in info['siblings']
             if s['rfilename'].endswith(('.json', '.safetensors', '.model', '.txt')) or s['rfilename'] == 'tokenizer.model']
    headers = {'Authorization': f'Bearer {os.environ["HF_TOKEN"]}'} if os.environ.get('HF_TOKEN') else {}
    for f in files:
        out = dest / f
        if out.exists(): continue
        part = out.with_suffix(out.suffix + '.part')
        have = part.stat().st_size if part.exists() else 0
        url = f'https://huggingface.co/{model}/resolve/{revision}/{urllib.parse.quote(f)}'
        req = urllib.request.Request(url, headers={**headers, **({'Range': f'bytes={have}-'} if have else {})})
        log(f'download {f}' + (f' (resume at {have / 1e9:.1f} GB)' if have else ''))
        with urllib.request.urlopen(req) as r, open(part, 'ab' if have else 'wb') as fh:
            shutil.copyfileobj(r, fh, 16 << 20)
        part.rename(out)


# ---------------------------------------------------------------- 2. convert
def convert_env(work, tag):
    """llama.cpp checkout at the binaries' tag + a py3.12 venv with its convert requirements."""
    src = work / f'llama.cpp-{tag}'
    if not (src / 'convert_hf_to_gguf.py').exists():
        run(['git', 'clone', '--depth', '1', '--branch', tag, 'https://github.com/ggml-org/llama.cpp', src])
    venv = work / '.venv-convert'
    py = venv / 'bin' / 'python'
    if not py.exists():
        req = src / 'requirements/requirements-convert_hf_to_gguf.txt'
        if shutil.which('uv'):
            run(['uv', 'venv', '--python', '3.12', venv])
            run(['uv', 'pip', 'install', '--python', py, '-r', req, '--index-strategy', 'unsafe-best-match'])
            run(['uv', 'pip', 'install', '--python', py, src / 'gguf-py', 'pyarrow<19'])
        else:
            base = shutil.which('python3.12') or sys.exit('need uv or python3.12 for the conversion venv')
            run([base, '-m', 'venv', venv])
            run([py, '-m', 'pip', 'install', '-r', req, src / 'gguf-py', 'pyarrow<19'])
    return src, py


def tensor_types(py, gguf):
    """Return {'router': types of ffn_gate_inp, 'output': type of output.weight} using gguf-py."""
    code = ('import sys,collections; from gguf import GGUFReader\n'
            'r=GGUFReader(sys.argv[1]); t=collections.defaultdict(set)\n'
            'for x in r.tensors:\n'
            '  k="router" if "ffn_gate_inp" in x.name else "output" if x.name=="output.weight" else "embd" if x.name=="token_embd.weight" else None\n'
            '  if k: t[k].add(x.tensor_type.name)\n'
            'o="|".join(sorted(t["output"])) or "tied:"+"|".join(sorted(t["embd"]))\n'
            'print(("|".join(sorted(t["router"])) or "-")+" "+o)')
    out = subprocess.run([str(py), '-c', code, str(gguf)], capture_output=True, text=True, check=True).stdout.split()
    return {'router': out[0], 'output': out[1]}


# ---------------------------------------------------------------- eval data
def load_eval(path):
    data = json.load(open(path))
    items = data.get('items') or data.get('data') or data.get('questions') if isinstance(data, dict) else data
    out = []
    for i, it in enumerate(items):
        q = it.get('question') or it.get('prompt') or it.get('input') or it.get('problem')
        ch = it.get('choices') or it.get('options')
        if isinstance(ch, dict): ch = [ch[k] for k in sorted(ch)]
        ans = it.get('answer', it.get('target', it.get('label', it.get('solution'))))
        if isinstance(ch, list) and isinstance(ans, int): ans = 'ABCDEFGHIJ'[ans]
        elif isinstance(ch, list) and isinstance(ans, str) and ans in ch and len(ans) > 1: ans = 'ABCDEFGHIJ'[ch.index(ans)]
        kind = it.get('kind') or ('mcq' if ch else 'numeric' if re.fullmatch(r'-?[\d,.]+', str(ans).split('####')[-1].strip()) else 'exact')
        out.append(dict(id=it.get('id', i), question=q, choices=ch, answer=str(ans), kind=kind, subset=it.get('subset', it.get('source', kind))))
    return out


STANDIN_SRC = {  # pinned parquet files of the public test splits
    'mmlu': 'https://huggingface.co/datasets/cais/mmlu/resolve/c30699e8356da336a370243923dbaf21066bb9fe/all/test-00000-of-00001.parquet',
    'gsm8k': 'https://huggingface.co/datasets/openai/gsm8k/resolve/740312add88f781978c0658806c59bc2815b9866/main/test-00000-of-00001.parquet',
}


def make_standin(path, py, n_each=100, seed=0):
    """Stand-in until G9's eval_mini_v0.json: random MMLU test (MCQ) + GSM8K test (numeric) items."""
    files = {}
    for k, url in STANDIN_SRC.items():
        files[k] = Path(path).parent / f'standin-{k}.parquet'
        if not files[k].exists(): urllib.request.urlretrieve(url, files[k])
    code = ('import sys,json,random,pyarrow.parquet as pq\n'
            'm=pq.read_table(sys.argv[1]).to_pylist(); g=pq.read_table(sys.argv[2]).to_pylist(); n=int(sys.argv[3])\n'
            'r=random.Random(int(sys.argv[4])); m=r.sample(m,n); g=r.sample(g,n)\n'
            'it=[dict(id=f"mmlu-{i}",question=x["question"],choices=list(x["choices"]),answer="ABCD"[x["answer"]],kind="mcq",subset="mmlu/"+x["subject"]) for i,x in enumerate(m)]\n'
            'it+=[dict(id=f"gsm8k-{i}",question=x["question"],answer=x["answer"].split("####")[-1].strip(),kind="numeric",subset="gsm8k") for i,x in enumerate(g)]\n'
            'print(json.dumps(it))')
    out = subprocess.run([str(py), '-c', code, str(files['mmlu']), str(files['gsm8k']), str(n_each), str(seed)],
                         capture_output=True, text=True, check=True).stdout
    items = json.loads(out)
    json.dump({'name': f'standin-v0 (mmlu{n_each}+gsm8k{n_each}, seed {seed})', 'items': items}, open(path, 'w'), indent=1)
    log(f'stand-in eval written: {path} ({len(items)} items)')


def prompt_for(it):
    if it['kind'] == 'mcq':
        opts = '\n'.join(f'{"ABCDEFGHIJ"[i]}. {c}' for i, c in enumerate(it['choices']))
        return f'{it["question"]}\n\n{opts}\n\nAnswer with the letter of the correct option only.'
    if it['kind'] == 'numeric':
        return f'{it["question"]}\n\nSolve step by step, then give the final answer on the last line as "Answer: <number>".'
    return it['question']


# Few-shot shots for base models (plain completion). Written for this script, not taken from any test set.
SHOTS_MCQ = ('Question: Which planet is closest to the Sun?\nA. Venus\nB. Mercury\nC. Earth\nD. Mars\nAnswer: B\n\n'
             'Question: What is the chemical symbol for sodium?\nA. S\nB. So\nC. Na\nD. Sd\nAnswer: C\n\n')
SHOTS_NUM = ('Question: A box holds 6 eggs. How many eggs are in 7 boxes?\n'
             'Answer: Each box holds 6 eggs, so 7 boxes hold 7 * 6 = 42 eggs. The answer is 42.\n\n'
             'Question: Tom had 50 dollars. He spent 18 dollars on a book and 7 dollars on lunch. How much money is left?\n'
             'Answer: He spent 18 + 7 = 25 dollars. He has 50 - 25 = 25 dollars left. The answer is 25.\n\n'
             'Question: A train travels 60 km per hour for 3 hours, then 40 km per hour for 2 hours. How far does it go?\n'
             'Answer: First 60 * 3 = 180 km, then 40 * 2 = 80 km. In total 180 + 80 = 260 km. The answer is 260.\n\n')
STOP = ['\n\nQuestion:', '\nQuestion:']


def completion_prompt_for(it):
    if it['kind'] == 'mcq':
        opts = '\n'.join(f'{"ABCDEFGHIJ"[i]}. {c}' for i, c in enumerate(it['choices']))
        return f'{SHOTS_MCQ}Question: {it["question"]}\n{opts}\nAnswer:'
    if it['kind'] == 'numeric':
        return f'{SHOTS_NUM}Question: {it["question"]}\nAnswer:'
    return f'Question: {it["question"]}\nAnswer:'


def score_item(it, text):
    if it['kind'] == 'mcq':
        m = re.search(r'(?:answer\s*(?:is)?\s*[:\-]?\s*\(?)([A-J])\b', text, re.I) or re.search(r'\b([A-J])\b', text)
        return bool(m) and m.group(1).upper() == it['answer'].strip().upper()[:1]
    if it['kind'] == 'numeric':
        tail = re.split(r'Answer:|The answer is', text)[-1]
        nums = re.findall(r'-?\d[\d,]*\.?\d*', tail)
        if not nums: return False
        norm = lambda s: float(s.replace(',', '').rstrip('.'))
        try: return abs(norm(nums[-1]) - norm(it['answer'].split('####')[-1].strip())) < 1e-6
        except ValueError: return False
    return text.strip().lower() == it['answer'].strip().lower()


# ---------------------------------------------------------------- 4. serve + eval
def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def evaluate(server_bin, gguf, items, args):
    port = free_port()
    cmd = [server_bin, '-m', str(gguf), '--port', str(port), '-ngl', str(args.ngl), '-c', str(args.ctx), '--temp', '0',
           '--seed', '0', '--no-webui', '-np', '1']
    log('$', ' '.join(cmd))
    srv = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=open(Path(args.work) / 'llama-server.log', 'ab'))
    try:
        base = f'http://127.0.0.1:{port}'
        for _ in range(600):
            try:
                if json.load(urllib.request.urlopen(base + '/health', timeout=2)).get('status') == 'ok': break
            except Exception: pass
            if srv.poll() is not None: sys.exit(f'llama-server exited, see {args.work}/llama-server.log')
            time.sleep(1)
        correct, by_kind, tps, t0 = 0, {}, [], time.time()
        for n, it in enumerate(items, 1):
            max_tok = args.max_tokens_mcq if it['kind'] == 'mcq' else args.max_tokens
            if args.prompt_mode == 'chat':
                url, body = '/v1/chat/completions', {'messages': [{'role': 'user', 'content': prompt_for(it)}]}
            else:
                url, body = '/v1/completions', {'prompt': completion_prompt_for(it), 'stop': STOP}
            body.update(temperature=0, seed=0, max_tokens=max_tok)
            req = urllib.request.Request(base + url, json.dumps(body).encode(), {'Content-Type': 'application/json'})
            r = json.load(urllib.request.urlopen(req, timeout=600))
            c = r['choices'][0]
            text = (c['message']['content'] if args.prompt_mode == 'chat' else c['text']) or ''
            ok = score_item(it, text)
            correct += ok
            k = by_kind.setdefault(it['kind'], [0, 0]); k[0] += ok; k[1] += 1
            if r.get('timings', {}).get('predicted_per_second'): tps.append(r['timings']['predicted_per_second'])
            if n % 25 == 0: log(f'  {n}/{len(items)} acc so far {correct / n:.3f}')
        return dict(score=correct / len(items), by_kind={k: round(a / b, 4) for k, (a, b) in by_kind.items()},
                    eval_time=time.time() - t0, tps=sum(tps) / len(tps) if tps else 0)
    finally:
        srv.send_signal(signal.SIGINT)
        try: srv.wait(30)
        except subprocess.TimeoutExpired: srv.kill()


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--model', default='allenai/OLMoE-1B-7B-0924')
    ap.add_argument('--revision', default='6d84c48581ece794365f2b8e9cfb043c68ade9c5')
    ap.add_argument('--prompt-mode', choices=['auto', 'chat', 'completion'], default='auto',
                    help='auto = chat for *Instruct* models, few-shot completion for base models')
    ap.add_argument('--formats', default=DEFAULT_FORMATS, help='comma list; bf16 = the unquantized baseline')
    ap.add_argument('--eval', help='eval JSON (G9 eval_mini_v0.json). Omit to build/use the stand-in set.')
    ap.add_argument('--limit', type=int, help='use only the first N eval items (smoke test)')
    ap.add_argument('--work', default=str(Path.home() / '.cache/era-v5-quant'))
    ap.add_argument('--runs-csv', default=str(DEFAULT_RUNS))
    ap.add_argument('--llama-bin', help='directory with llama-quantize / llama-server (default: PATH)')
    ap.add_argument('--ngl', type=int, default=99, help='layers on GPU')
    ap.add_argument('--ctx', type=int, default=4096)
    ap.add_argument('--max-tokens', type=int, default=512)
    ap.add_argument('--max-tokens-mcq', type=int, default=16)
    ap.add_argument('--delete-hf', action='store_true', help='delete the HF download after the bf16 GGUF exists')
    ap.add_argument('--cleanup', action='store_true', help='delete each quantized GGUF after its eval')
    ap.add_argument('--no-record', action='store_true', help='do not append to runs.csv or write runs/manifest_<date>.json')
    ap.add_argument('--notes', default='')
    args = ap.parse_args()

    work = Path(args.work).expanduser(); work.mkdir(parents=True, exist_ok=True); args.work = str(work)
    if args.prompt_mode == 'auto':
        args.prompt_mode = 'chat' if re.search(r'instruct|chat', args.model, re.I) else 'completion'
    qbin, sbin = (find_bin(b, args.llama_bin) for b in ('llama-quantize', 'llama-server'))
    build, commit = llama_build(sbin)  # llama-quantize does not print its version
    tag = llama_tag(build, commit)
    runtime = f'llama.cpp {tag} ({commit})'
    machine = machine_string()
    log(f'{runtime} | {machine}')

    name = args.model.split('/')[-1]
    hf_dir, bf16 = work / 'hf' / name, work / f'{name}-bf16.gguf'
    src, py = convert_env(work, tag)
    if not bf16.exists():
        hf_download(args.model, args.revision, hf_dir)
        run([py, src / 'convert_hf_to_gguf.py', hf_dir, '--outtype', 'bf16', '--outfile', bf16])
    if args.delete_hf and hf_dir.exists():
        shutil.rmtree(hf_dir); log('deleted HF download')

    if args.eval:
        eval_path = Path(args.eval)
    else:
        eval_path = work / 'eval_standin_v0.json'
        if not eval_path.exists(): make_standin(eval_path, py)
    items = load_eval(eval_path)
    if args.limit is not None:  # seeded sample so a smoke test covers every subset
        items = random.Random(0).sample(items, min(args.limit, len(items)))
    meta = json.load(open(eval_path))
    eval_name = (meta.get('name') if isinstance(meta, dict) else None) or eval_path.name
    log(f'eval: {eval_name}, {len(items)} items')

    n_params = None
    for fmt in [f.strip() for f in args.formats.split(',') if f.strip()]:
        out = bf16 if fmt.lower() == 'bf16' else work / f'{name}-{fmt}.gguf'
        qtime = 0.0
        if not out.exists():
            t0 = time.time()
            # Q8_0 already is 8-bit everywhere; lower formats keep the output layer at Q8_0.
            extra = [] if fmt.upper() == 'Q8_0' else ['--output-tensor-type', 'q8_0']
            with open(work / f'quantize-{fmt}.log', 'w') as qlog:
                run([qbin, *extra, bf16, out, fmt], stdout=qlog, stderr=subprocess.STDOUT)
            qtime = time.time() - t0
            out.with_suffix('.quant_time').write_text(f'{qtime:.1f}')
        elif out.with_suffix('.quant_time').exists():  # reused GGUF: report the time it took when it was made
            qtime = float(out.with_suffix('.quant_time').read_text())
        types = tensor_types(py, out)
        ok8 = {'F32', 'BF16', 'F16', 'Q8_0'}
        bad_router = types['router'] != '-' and not set(types['router'].split('|')) <= ok8
        bad_output = not types['output'].startswith('tied:') and types['output'] not in ok8  # tied = dense test models only
        if bad_router or bad_output:
            sys.exit(f'{fmt}: router {types["router"]} / output {types["output"]} is below 8 bits, which breaks the G12 rule')
        size = out.stat().st_size
        if n_params is None:  # bf16 = 2 bytes per weight
            n_params = bf16.stat().st_size / 2
        if not args.no_record:  # hash before eval, so a failed eval still records the file that was measured
            record_manifest(args.runs_csv, out, fmt, args.model, args.revision)
        res = evaluate(sbin, out, items, args)
        row = dict(date=datetime.date.today().isoformat(), model=args.model, revision=args.revision[:12], format=fmt,
                   bpw=round(8 * size / n_params, 2), size_gb=round(size / 1e9, 2), router_type=types['router'],
                   output_type=types['output'], eval_set=eval_name, n_items=len(items), score=round(res['score'], 4),
                   score_by_kind=json.dumps(res['by_kind']), quant_time_s=round(qtime, 1), eval_time_s=round(res['eval_time'], 1),
                   gen_tok_s=round(res['tps'], 1), machine=machine, runtime=runtime,
                   notes='; '.join(x for x in [f'prompt={args.prompt_mode}', args.notes, f'limit={args.limit}' if args.limit is not None else ''] if x))
        log(f'{fmt}: score {row["score"]} {row["score_by_kind"]} | {row["size_gb"]} GB, {row["bpw"]} bpw | '
            f'quant {row["quant_time_s"]}s, eval {row["eval_time_s"]}s, {row["gen_tok_s"]} tok/s')
        if not args.no_record:
            p = Path(args.runs_csv); p.parent.mkdir(parents=True, exist_ok=True)
            new = not p.exists()
            with open(p, 'a', newline='') as f:
                w = csv.DictWriter(f, fieldnames=RUN_FIELDS)
                if new: w.writeheader()
                w.writerow(row)
        if args.cleanup and out != bf16:
            out.unlink(); log(f'deleted {out.name}')


if __name__ == '__main__':
    main()
