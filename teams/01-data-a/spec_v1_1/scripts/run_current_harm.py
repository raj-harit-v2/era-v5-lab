"""Validate the rebuilt cleaner with the existing G1 and G2 harm engines. IDs/counts only."""
import argparse, csv, hashlib, importlib.util, json, sys
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--packs',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
OUT=args.out.resolve();OUT.mkdir(parents=True,exist_ok=True)
PACKS=args.packs.resolve()
A=ROOT/'teams/01-data-a'; B=ROOT/'teams/02-data-b'
sys.path.insert(0,str(A/'harmtest'))
import harm_test as ht

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
c=load('rebuilt_clean',A/'spec_v1_1/clean.py')
db=load('indic_harm',B/'tools/harm_test_indic.py')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
scope=json.loads((A/'jobs/2026-11-19-first-training/approved_inputs.json').read_text())
meta={'cleaner_sha256':sha(Path(c.__file__)),'sheet_sha256':sha(A/'spec_v1_1/sheets/specv1_1.md'),'shared_f1_sha256':sha(A/'spec_v1_1/build/f1_rule.py'),'adapter_sha256':sha(Path(__file__)),'data_a_harm_sha256':sha(Path(ht.__file__)),'data_b_harm_sha256':sha(Path(db.__file__)),'packs_root':str(PACKS),'limit_percent':1,'timeout_seconds':5,'legacy_suite':'blocked: historical spec/spec_v1.md absent','packs':[]}

def indic_result(name,fn,docs):
    result={k:[] for k in ('changed','dropped','errors','joiners','form')}
    for id_,doc in docs.items():
        def step(text):return fn(dict(doc,text=text))
        row=db.run_rule(name,[step],[(doc['pack_id'],id_,doc['text'])],5)
        for key in result: result[key].extend(row[key])
    return {'rule':name,'result':db.verdict_of(result,len(docs),Fraction(1)),**result}

for pack in scope['allowed_train_packs']:
    team=B if pack.startswith(('ind-','cadj-')) else A
    gold=team/'gold'/f'{pack}_gold.csv'; parquet=PACKS/f'{pack}.parquet'
    record={'pack':pack,'team':team.name,'supported':pack in c._FAMILY,'gold':str(gold.relative_to(ROOT)),'pack_sha256':sha(parquet),'status':'NOT_TESTABLE'}
    if not gold.exists():
        record['reason']='gold file missing'
    else:
        record['gold_sha256']=sha(gold)
        try:
            ids=ht.read_gold(gold);docs=ht.read_pack_docs(parquet,ids)
            for doc in docs.values():doc['pack_id']=pack
            family=c._FAMILY.get(pack)
            factories=(*c._PIPELINES[family],c._shared_f1_rule) if family else ()
            rules=[(c._ID[f],f()) for f in factories if pack in c.SCOPE[c._ID[f]]]
            results=[ht._result(rid,ht.run_rule(fn,docs,5),len(docs),Fraction(1)) for rid,fn in rules]
            pipeline=ht._result('clean()',ht.run_rule(c.clean,docs,5),len(docs),Fraction(1))
            record.update(gold_count=len(docs),rules_alone=results,pipeline=pipeline)
            record['status']='ERROR' if any(r['result']=='ERROR' for r in results+[pipeline]) else 'FAIL' if any(r['result']!='PASS' for r in results+[pipeline]) else 'PASS'
            if team==B:
                record['indic_rules']=[indic_result(rid,fn,docs) for rid,fn in rules]
                record['indic_pipeline']=indic_result('clean()',c.clean,docs)
                if any(r['result']!='PASS' for r in record['indic_rules']+[record['indic_pipeline']]):record['status']='FAIL'
        except ht.NotTestable:
            record['reason']='gold set empty'
        except Exception as exc:
            record['status']='ERROR';record['reason']=type(exc).__name__
    (OUT/f'{pack}.json').write_text(json.dumps(record,indent=2)+'\n')
    meta['packs'].append({k:v for k,v in record.items() if k not in ('rules_alone','indic_rules','pipeline','indic_pipeline')})
    print(pack,record['status'],'gold',record.get('gold_count','-'),'supported',record['supported'],flush=True)
    (OUT/'summary.json').write_text(json.dumps(meta,indent=2)+'\n')
print('COMPLETE',flush=True)

reports={p['pack']:json.loads((OUT/f"{p['pack']}.json").read_text()) for p in meta['packs']}
(OUT/'reports.json').write_text(json.dumps(reports,indent=2)+'\n')
with (OUT/'summary.csv').open('w',newline='') as stream:
    fields=['pack','status','supported','gold_count','changed','dropped','errors','failing_rules','reason']
    writer=csv.DictWriter(stream,fieldnames=fields)
    writer.writeheader()
    for record in reports.values():
        pipeline=record.get('pipeline',{})
        writer.writerow({**{key:record.get(key,'') for key in fields[:4]},
                         **{key:pipeline.get(key,'') for key in ('changed','dropped','errors')},
                         'failing_rules':';'.join(r['rule'] for r in record.get('rules_alone',[]) if r['result']!='PASS'),
                         'reason':record.get('reason','')})

sys.exit(1 if any(p["status"] != "PASS" for p in meta["packs"]) else 0)
