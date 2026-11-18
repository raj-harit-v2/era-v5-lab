#!/usr/bin/env python3
"""G12: bf16 baseline + llama.cpp quantization ladder + eval, one command.

    python teams/12-quantization/scripts/quantize_eval.py --eval <eval_mini_v0.json>                 # a Hub model (week 1)
    python teams/12-quantization/scripts/quantize_eval.py --checkpoint <run dir> \\
        --tokenizer teams/03-tokenizer/release/tokenizer.json --eval <items.json>                    # our checkpoint (week 3)

Steps (each one is skipped when its output already exists, so a rerun resumes):
  1. get the Hugging Face model folder:
       --model/--revision   download it from the Hub (plain HTTPS, pinned revision)
       --checkpoint         a G5 checkpoint (train_week2.py run folder, checkpoint.pt or model.safetensors) is
                            exported with export_hf.py as Granite MoE Shared, and test A1 (same logits as G5's model)
                            must pass; a folder that already has config.json is used as it is. After step 2,
                            check_gguf_logits.py (test A3) compares llama.cpp on the bf16 GGUF with G5's model and
                            its result is reported
  2. convert it to a bf16 GGUF with llama.cpp's convert_hf_to_gguf.py, at the same llama.cpp
     build as the installed binaries (a private Python 3.12 venv is made for steps 1 and 2 only).
     With --tokenizer the GGUF carries that tokenizer.json (it must have --tokenizer-sha256, default the frozen
     tokenizer, p1536) and the pre-tokenizer is set to granite-embed-multi-97m, the only llama.cpp type that splits
     Indic text like tokenizer.json does (docs/unsupported_parts.md, section 4a). --roundtrip then runs
     tokenizer/gguf_roundtrip.py on the GGUF: the same token ids as tokenizer.json on held-out text. Its exit code
     (0 same ids, 2 only the dropped normalizer differs, 1 anything else) is reported, and does not stop the run
  3. quantize to each format; router gates (ffn_gate_inp) are never quantized by llama.cpp
     and the output layer is forced to Q8_0; both are checked in the GGUF and written to runs.csv.
     Each GGUF's SHA-256 is written to runs/manifest_<date>.json (same folder as runs.csv)
  4. serve each GGUF with llama-server, run the eval, append one row per format to runs.csv

Out: the GGUF files in --work, one runs.csv row per format, and --scores-out (default <work>/<name>-scores.json):
the checkpoint and tokenizer hashes, the A1 result, and for each format the file, its SHA-256, size and scores.

Needs: llama.cpp binaries on PATH (brew install llama.cpp) or --llama-bin, and uv or python3.12.
Big files live in --work (default ~/.cache/era-v5-quant), never in the repo.
Disk: about 14 GB HF + 14 GB bf16 GGUF + 28 GB for the six quants (use --delete-hf / --cleanup to save space).
"""
import argparse, csv, datetime, hashlib, json, os, platform, random, re, shutil, signal, socket, subprocess, sys, time
import urllib.error, urllib.parse, urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNS = REPO_ROOT / 'teams/12-quantization/runs/runs.csv'
DEFAULT_FORMATS = 'bf16,Q8_0,Q6_K,Q5_K_M,Q4_K_M,Q3_K_M,Q2_K'
RUN_FIELDS = ['date', 'model', 'revision', 'format', 'bpw', 'size_gb', 'router_type', 'output_type', 'eval_set',
              'n_items', 'score', 'score_by_kind', 'quant_time_s', 'eval_time_s', 'gen_tok_s', 'machine', 'runtime', 'notes']
EXPORT_HF = Path(__file__).resolve().with_name('export_hf.py')
CHECK_GGUF = Path(__file__).resolve().with_name('check_gguf_logits.py')
TOKENIZER_DIR = REPO_ROOT / 'teams/12-quantization/tokenizer'
ROUNDTRIP_PACKAGES = ['llama-cpp-python==0.3.36', 'datasets==4.8.5', 'regex']  # the versions in gguf_roundtrip.py
ROUNDTRIP_VERDICT = {0: 'same token ids on every line', 2: 'differences only on lines the normalizer changes (GGUF has no normalizer)',
                     1: 'differences the dropped normalizer does not explain, on lines or in the whole-vocabulary check: read the report'}
# teams/03-tokenizer/release/README.md: the frozen tokenizer, p1536 (16 Nov 2026; it replaced C3 sample-v0)
FROZEN_TOKENIZER_SHA256 = 'e6b93a93a60520d7b1af2e9242485f443b5596a1e116b8f8798d83bbad25a64b'
PRE_TOKENIZER = 'granite-embed-multi-97m'
TOKENIZER_FILES = ('tokenizer.json', 'tokenizer_config.json', 'tokenizer.model', 'special_tokens_map.json',
                   'vocab.json', 'merges.txt', 'added_tokens.json', 'chat_template.jinja', 'chat_template.json')
WINDOWS = platform.system() == 'Windows'


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
    p = Path(bindir) / (name + '.exe' if WINDOWS else name) if bindir else shutil.which(name)
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
    py = venv / 'Scripts' / 'python.exe' if WINDOWS else venv / 'bin' / 'python'
    extra = [src / 'gguf-py', 'pyarrow<19']
    if not py.exists():
        req = src / 'requirements/requirements-convert_hf_to_gguf.txt'
        if shutil.which('uv'):
            run(['uv', 'venv', '--python', '3.12', venv])
            run(['uv', 'pip', 'install', '--python', py, '-r', req, '--index-strategy', 'unsafe-best-match'])
            run(['uv', 'pip', 'install', '--python', py, *extra])
        else:
            base = shutil.which('python3.12') or sys.exit('need uv or python3.12 for the conversion venv')
            run([base, '-m', 'venv', venv])
            run([py, '-m', 'pip', 'install', '-r', req, *extra])
    return src, py


def convert(py, src, model_dir, outfile, pre=None):
    """HF folder -> bf16 GGUF. `pre` sets the pre-tokenizer type by name: the stock converter stops on a tokenizer
    whose hash it does not know ("BPE pre-tokenizer was not recognized"), and ours is not in its list."""
    if pre is None:
        return run([py, src / 'convert_hf_to_gguf.py', model_dir, '--outtype', 'bf16', '--outfile', outfile])
    sys.path.insert(0, str(TOKENIZER_DIR))
    import gguf_roundtrip  # the forced pre-tokenizer conversion that tokenizer/convert_frozen.py uses
    log(f'$ convert_hf_to_gguf.py (pre-tokenizer {pre}) {model_dir} --outtype bf16 --outfile {outfile}')
    gguf_roundtrip.convert(src, model_dir, pre, outfile, 'bf16', py)


def tokenizer_ids(tokenizer_json):
    """Number of ids a tokenizer.json needs in the embedding table."""
    t = json.loads(Path(tokenizer_json).read_text(encoding='utf-8'))
    return 1 + max(max(t['model']['vocab'].values()), max((a['id'] for a in t.get('added_tokens', [])), default=0))


def stage_tokenizer(model_dir, tokenizer_json, out, bos, eos):
    """`out` = the model folder's files (links, or copies where the file system has no links) with its own tokenizer
    files replaced by tokenizer.json. As stage() in tokenizer/convert_frozen.py, which uses symlinks; Windows refuses
    those without a privilege, so this one makes hard links or copies."""
    have = json.loads((model_dir / 'config.json').read_text(encoding='utf-8')).get('vocab_size', 0)
    if have < tokenizer_ids(tokenizer_json):
        sys.exit(f'refusing: the tokenizer has {tokenizer_ids(tokenizer_json):,} ids, the checkpoint\'s embedding table {have:,}')
    out.mkdir(parents=True, exist_ok=True)
    for f in model_dir.iterdir():
        if f.name in TOKENIZER_FILES or (out / f.name).exists() or not f.is_file(): continue
        try: os.link(f, out / f.name)
        except OSError: shutil.copyfile(f, out / f.name)
    shutil.copyfile(tokenizer_json, out / 'tokenizer.json')
    (out / 'tokenizer_config.json').write_text(json.dumps(
        {'tokenizer_class': 'PreTrainedTokenizerFast', 'bos_token': bos, 'eos_token': eos}), encoding='utf-8')
    return out


def prepare_checkpoint(args, py, work, name):
    """--checkpoint -> (HF folder ready for the converter, export report or None)."""
    ckpt = Path(args.checkpoint).expanduser()
    if (ckpt / 'config.json').exists():  # already a Hugging Face folder
        return (stage_tokenizer(ckpt, Path(args.tokenizer), work / 'hf' / name, args.bos, args.eos) if args.tokenizer else ckpt), None
    if not args.tokenizer:
        sys.exit('--checkpoint is a G5 checkpoint, which has no tokenizer: pass --tokenizer <tokenizer.json>')
    out = work / 'hf' / name
    report = out / 'export_report.json'
    if not report.exists():  # the report is written last, so a folder without it is a broken export
        if out.exists(): shutil.rmtree(out)
        run([py, EXPORT_HF, '--checkpoint', ckpt, '--out', out, '--tokenizer', args.tokenizer, '--bos', args.bos,
             '--eos', args.eos, '--verify', args.verify, *(['--spec', args.spec] if args.spec else [])])
    return out, json.loads(report.read_text(encoding='utf-8'))


def roundtrip(args, py, src, work, name, bf16):
    """Run tokenizer/gguf_roundtrip.py on the bf16 GGUF: does llama.cpp give the token ids of tokenizer.json?"""
    out = work / f'{name}-roundtrip'
    result = out / 'result.json'
    if not result.exists():
        if subprocess.run([str(py), '-c', 'import llama_cpp, datasets, regex'], capture_output=True).returncode:
            run(['uv', 'pip', 'install', '--python', py, *ROUNDTRIP_PACKAGES] if shutil.which('uv')
                else [py, '-m', 'pip', 'install', *ROUNDTRIP_PACKAGES])
        cmd = [py, TOKENIZER_DIR / 'gguf_roundtrip.py', '--tokenizer', args.tokenizer, '--name', name, '--gguf', bf16,
               '--normalize-first', '--llama-cpp', src, '--work', work / 'roundtrip', '--out', out, '--pre', PRE_TOKENIZER,
               '--bos', args.bos, '--eos', args.eos]
        log('$', ' '.join(map(str, cmd)))
        code = subprocess.run(list(map(str, cmd)), env=dict(os.environ, PYTHONUTF8='1')).returncode
        if code not in ROUNDTRIP_VERDICT or not (out / f'gguf_roundtrip_{name}.md').exists():
            sys.exit(f'the tokenizer round trip did not finish (exit code {code})')
        result.write_text(json.dumps(dict(exit_code=code, verdict=ROUNDTRIP_VERDICT[code],
                                          report=str(out / f'gguf_roundtrip_{name}.md'))), encoding='utf-8')
    r = json.loads(result.read_text(encoding='utf-8'))
    log(f'tokenizer round trip: exit code {r["exit_code"]}, {r["verdict"]}. Report: {r["report"]}')
    return r


def checkpoint_weights(path):
    """The file that holds the weights of a --checkpoint (hashed for its name and the revision column)."""
    path = Path(path).expanduser()
    if path.is_file(): return path
    found = [path / n for n in ('checkpoint.pt', 'model.safetensors') if (path / n).exists()] or sorted(path.glob('*.safetensors'))
    if not found: sys.exit(f'{path}: no checkpoint.pt or *.safetensors')
    return found[0]


def gguf_meta(py, gguf):
    """Architecture, trained context, pre-tokenizer, vocabulary size and EOS id of a GGUF, using gguf-py."""
    code = ('import sys,json; from gguf import GGUFReader\n'
            'r=GGUFReader(sys.argv[1]); f=r.fields\n'
            'def s(k): return f[k].contents() if k in f else None\n'
            'a=s("general.architecture")\n'
            'print(json.dumps(dict(arch=a,n_ctx_train=s(a+".context_length"),pre=s("tokenizer.ggml.pre"),'
            'n_vocab=len(f["tokenizer.ggml.tokens"].data),eos_id=s("tokenizer.ggml.eos_token_id"))))')
    return json.loads(subprocess.run([str(py), '-c', code, str(gguf)], capture_output=True, text=True, check=True).stdout)


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
    data = json.load(open(path, encoding='utf-8'))
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
    json.dump({'name': f'standin-v0 (mmlu{n_each}+gsm8k{n_each}, seed {seed})', 'items': items}, open(path, 'w', encoding='utf-8'), indent=1)
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


def evaluate(server_bin, gguf, items, args, ctx):
    port = free_port()
    cmd = [server_bin, '-m', str(gguf), '--port', str(port), '-ngl', str(args.ngl), '-c', str(ctx), '--temp', '0',
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
        correct, by_kind, tps, rejected, t0 = 0, {}, [], 0, time.time()
        for n, it in enumerate(items, 1):
            max_tok = args.max_tokens_mcq if it['kind'] == 'mcq' else args.max_tokens
            if args.prompt_mode == 'chat':
                url, body = '/v1/chat/completions', {'messages': [{'role': 'user', 'content': prompt_for(it)}]}
            else:
                url, body = '/v1/completions', {'prompt': completion_prompt_for(it), 'stop': STOP}
            body.update(temperature=0, seed=0, max_tokens=max_tok)
            req = urllib.request.Request(base + url, json.dumps(body).encode(), {'Content-Type': 'application/json'})
            try:
                r = json.load(urllib.request.urlopen(req, timeout=600))
            except urllib.error.HTTPError as e:
                if e.code != 400: raise
                # the server refuses a prompt longer than the context (small test models). The item counts as
                # wrong and the number of such items goes into the row, so the score is never silently partial.
                rejected += 1
                r = {'choices': [{'text': '', 'message': {'content': ''}}]}
            c = r['choices'][0]
            text = (c['message']['content'] if args.prompt_mode == 'chat' else c['text']) or ''
            ok = score_item(it, text)
            correct += ok
            k = by_kind.setdefault(it['kind'], [0, 0]); k[0] += ok; k[1] += 1
            if r.get('timings', {}).get('predicted_per_second'): tps.append(r['timings']['predicted_per_second'])
            if n % 25 == 0: log(f'  {n}/{len(items)} acc so far {correct / n:.3f}')
        return dict(score=correct / len(items), by_kind={k: round(a / b, 4) for k, (a, b) in by_kind.items()},
                    eval_time=time.time() - t0, tps=sum(tps) / len(tps) if tps else 0, rejected=rejected)
    finally:
        srv.terminate() if WINDOWS else srv.send_signal(signal.SIGINT)  # Windows has no SIGINT for a child process
        try: srv.wait(30)
        except subprocess.TimeoutExpired: srv.kill()


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--model', default='allenai/OLMoE-1B-7B-0924')
    ap.add_argument('--revision', default='6d84c48581ece794365f2b8e9cfb043c68ade9c5')
    ap.add_argument('--checkpoint', help='our own checkpoint instead of --model: a G5 run folder, checkpoint.pt or '
                    'model.safetensors (exported with export_hf.py), or a Hugging Face folder with config.json')
    ap.add_argument('--spec', help='model settings for a G5 checkpoint without a manifest.json beside it (see export_hf.py)')
    ap.add_argument('--name', help='name for the files and the model column (default: the checkpoint folder or file name)')
    ap.add_argument('--tokenizer', help='tokenizer.json to put into the GGUF; needed for a G5 checkpoint')
    ap.add_argument('--tokenizer-sha256', default=FROZEN_TOKENIZER_SHA256,
                    help='SHA-256 that --tokenizer must have (default: the frozen tokenizer, p1536)')
    ap.add_argument('--bos', default='<|begin_of_text|>')
    ap.add_argument('--eos', default='<|endoftext|>', help='end of document in the frozen tokenizer')
    ap.add_argument('--verify', type=int, default=64, help='prompts for test A1 during the export of a G5 checkpoint')
    ap.add_argument('--roundtrip', action='store_true', help='also run tokenizer/gguf_roundtrip.py on the bf16 GGUF: llama.cpp '
                    'must give the token ids of --tokenizer on held-out text (downloads about 20 MB the first time)')
    ap.add_argument('--no-a3', action='store_true', help="skip test A3 (llama.cpp on the bf16 GGUF against G5's model)")
    ap.add_argument('--scores-out', help='JSON with the files, hashes and scores of this run (default: <work>/<name>-scores.json)')
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
    tok_sha = None
    if args.roundtrip and not args.tokenizer: ap.error('--roundtrip needs --tokenizer')
    if args.tokenizer:  # checked first: a wrong tokenizer must not cost an export and a conversion
        tok_sha = file_sha256(args.tokenizer)
        if tok_sha != args.tokenizer_sha256.lower():
            sys.exit(f'refusing: {args.tokenizer} has sha256 {tok_sha}, asked for {args.tokenizer_sha256}')
    if args.checkpoint:
        weights = checkpoint_weights(args.checkpoint)
        ckpt_sha = file_sha256(weights)
        base = args.name or (weights.parent.name if weights.name in ('checkpoint.pt', 'model.safetensors') else weights.stem)
        # the weights' hash is in every file name, so a new checkpoint under an old name never reuses old files
        name, model, revision = f'{base}-{ckpt_sha[:8]}', base, ckpt_sha
    else:
        name, model, revision = args.model.split('/')[-1], args.model, args.revision
    if args.prompt_mode == 'auto':
        args.prompt_mode = 'chat' if re.search(r'instruct|chat', model, re.I) else 'completion'
    qbin, sbin = (find_bin(b, args.llama_bin) for b in ('llama-quantize', 'llama-server'))
    build, commit = llama_build(sbin)  # llama-quantize does not print its version
    tag = llama_tag(build, commit)
    runtime = f'llama.cpp {tag} ({commit})'
    machine = machine_string()
    log(f'{runtime} | {machine}')

    hf_dir, bf16 = work / 'hf' / name, work / f'{name}-bf16.gguf'
    src, py = convert_env(work, tag)
    export = None
    if args.checkpoint:
        if (work / 'hf' / name / 'export_report.json').exists() or not bf16.exists():
            model_dir, export = prepare_checkpoint(args, py, work, name)
            if not bf16.exists(): convert(py, src, model_dir, bf16, PRE_TOKENIZER if args.tokenizer else None)
    elif not bf16.exists():
        hf_download(args.model, args.revision, hf_dir)
        if args.tokenizer:
            convert(py, src, stage_tokenizer(hf_dir, Path(args.tokenizer), work / 'hf' / f'{name}-staged', args.bos, args.eos),
                    bf16, PRE_TOKENIZER)
        else:
            convert(py, src, hf_dir, bf16)
    info = gguf_meta(py, bf16)
    if args.tokenizer and (info['pre'] != PRE_TOKENIZER or info['n_vocab'] < tokenizer_ids(args.tokenizer)):
        sys.exit(f'{bf16.name} does not carry --tokenizer (pre-tokenizer {info["pre"]}, {info["n_vocab"]:,} tokens): '
                 f'it was made without it; delete it and rerun')
    a3 = None
    if export is not None and not args.no_a3:  # test A3: llama.cpp on the bf16 GGUF against G5's model
        a3_path = work / f'{name}-a3.json'
        if not a3_path.exists():
            subprocess.run([str(py), str(CHECK_GGUF), '--checkpoint', str(Path(args.checkpoint).expanduser()), '--gguf', str(bf16),
                            '--llama-server', sbin, '--out', str(a3_path), *(['--spec', args.spec] if args.spec else [])])
        if not a3_path.exists(): sys.exit('test A3 did not run (see the error above); --no-a3 skips it')
        a3 = json.loads(a3_path.read_text(encoding='utf-8'))
        if not a3['passed']:  # reported, not fatal: the limit is not calibrated on a trained checkpoint yet
            log(f'WARNING: A3 failed: same top-1 on {a3["same_top1"]}/{a3["prompts"]} prompts, max log-probability '
                f'difference {a3["max_abs_logprob_diff"]:.4f}. Read check_gguf_logits.py before trusting the scores.')
    trip = roundtrip(args, py, src, work, name, bf16) if args.roundtrip else None
    if args.delete_hf and hf_dir.exists():
        shutil.rmtree(hf_dir); log('deleted HF download')
    ctx = min(args.ctx, info['n_ctx_train'] or args.ctx)  # never serve past the length the model was trained on
    if ctx < args.ctx: log(f'context {ctx} (the model\'s trained length), not --ctx {args.ctx}')

    if args.eval:
        eval_path = Path(args.eval)
    else:
        eval_path = work / 'eval_standin_v0.json'
        if not eval_path.exists(): make_standin(eval_path, py)
    items = load_eval(eval_path)
    if args.limit is not None:  # seeded sample so a smoke test covers every subset
        items = random.Random(0).sample(items, min(args.limit, len(items)))
    meta = json.load(open(eval_path, encoding='utf-8'))
    eval_name = (meta.get('name') if isinstance(meta, dict) else None) or eval_path.name
    log(f'eval: {eval_name}, {len(items)} items')

    scores_path = Path(args.scores_out).expanduser() if args.scores_out else work / f'{name}-scores.json'
    scores = dict(model=model, revision=revision, checkpoint=str(args.checkpoint or ''), tokenizer_sha256=tok_sha,
                  gguf=info, export_a1=(export or {}).get('verify'), gguf_a3=a3, tokenizer_roundtrip=trip, runtime=runtime, machine=machine,
                  eval_set=eval_name, n_items=len(items), prompt_mode=args.prompt_mode, context=ctx, formats=[])
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
            record_manifest(args.runs_csv, out, fmt, model, revision)
        res = evaluate(sbin, out, items, args, ctx)
        row = dict(date=datetime.date.today().isoformat(), model=model, revision=revision[:12], format=fmt,
                   bpw=round(8 * size / n_params, 2), size_gb=round(size / 1e9, 2), router_type=types['router'],
                   output_type=types['output'], eval_set=eval_name, n_items=len(items), score=round(res['score'], 4),
                   score_by_kind=json.dumps(res['by_kind']), quant_time_s=round(qtime, 1), eval_time_s=round(res['eval_time'], 1),
                   gen_tok_s=round(res['tps'], 1), machine=machine, runtime=runtime,
                   notes='; '.join(x for x in [f'prompt={args.prompt_mode}', args.notes, f'limit={args.limit}' if args.limit is not None else '',
                                               f'tokenizer={tok_sha[:12]}' if tok_sha else '',
                                               f'{res["rejected"]} prompts over the context' if res['rejected'] else ''] if x))
        log(f'{fmt}: score {row["score"]} {row["score_by_kind"]} | {row["size_gb"]} GB, {row["bpw"]} bpw | '
            f'quant {row["quant_time_s"]}s, eval {row["eval_time_s"]}s, {row["gen_tok_s"]} tok/s')
        if not args.no_record:
            p = Path(args.runs_csv); p.parent.mkdir(parents=True, exist_ok=True)
            new = not p.exists()
            with open(p, 'a', newline='') as f:
                w = csv.DictWriter(f, fieldnames=RUN_FIELDS)
                if new: w.writeheader()
                w.writerow(row)
        # written after every format, so a run that stops half way still leaves the scores it has
        scores['formats'].append(dict(row, score_by_kind=res['by_kind'], file=str(out), sha256=file_sha256(out),
                                      size_bytes=size, prompts_over_context=res['rejected']))
        scores_path.write_text(json.dumps(scores, indent=2) + '\n', encoding='utf-8')
        if args.cleanup and out != bf16:
            out.unlink(); log(f'deleted {out.name}')
    log(f'scores: {scores_path}')


if __name__ == '__main__':
    main()
