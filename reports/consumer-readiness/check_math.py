"""CPU-only evidence audit. Run from any cwd with the project .venv Python.
Writes math-checks.json; never changes stored runs or upstream sources.
"""
from pathlib import Path
import hashlib, importlib.util, itertools, json, os, subprocess, sys, time
os.environ['OTRECON_FORCE_RUPTURES']='1'
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
UP=ROOT/'vendor/forking-fast'
sys.path.insert(0,str(UP/'otrecon/tests'))
import numpy as np
from _baseline_loader import load_baseline
from otrecon import data as od
from otrecon.models import MODEL_REGISTRY, MultinomialCost
from otrecon.cv import cv_select
from live_service import reconstruct
from sampling import position_draws
spec=importlib.util.spec_from_file_location('audit_loader',UP/'data/loader.py')
loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)
base=load_baseline()
report={'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'python':sys.version.split()[0],
        'upstream_commit':subprocess.check_output(['git','-C',str(UP),'rev-parse','HEAD'],text=True).strip(),
        'upstream_clean':not subprocess.check_output(['git','-C',str(UP),'status','--porcelain'],text=True).strip(),
        'strict_ruptures':True,'checks':[]}
assert report['upstream_clean']
assert report['upstream_commit']=='d32fed8d4162a4888291c4b3a38b059727c85a41'

def add(name,**details):
    report['checks'].append({'name':name,'passed':True,**details});print(name,details,flush=True)
def err(a,b):
    a,b=np.asarray(a),np.asarray(b);assert a.shape==b.shape
    return float(np.max(np.abs(a-b))) if a.size else 0.0

manifest=json.loads((UP/'data/MANIFEST.json').read_text())
for rel,info in manifest['files'].items():
    assert hashlib.sha256((UP/'data'/rel).read_bytes()).hexdigest()==info['sha256']
add('released_store_hashes',files=len(manifest['files']))
for rel in manifest['files']:
    rec=loader.load_store(str(UP/'data'/rel));assert loader.matches_recorded(rec)
add('all_released_weighted_reference_curves_recompute',files=len(manifest['files']))

def direct_record(pos,draws,categories):
    n=draws.shape[1]
    return {'categories':categories,'sampling_design':'position_mixture_v1','base':{'finish_reason':'stop'},
      'config':{'cont_temperature':1},'positions':[{'t':int(t),'samples':n,'retained_mass':1.0} for t in pos],
      'branches':[{'t':int(t),'draw_indices':list(range(n)),'answers':[categories[i] for i in row],
                   'observations':[{'label':categories[i],'stop_reason':'eos'} for i in row]} for t,row in zip(pos,draws)]}

# Released-data outcome sequences transported through the live schema to isolate integration.
# Deliberately sparse across each source trace: not the paper's full evaluation grid.
for track,row in [('llama',12),('llama',39),('deepseek',12),('deepseek',39)]:
    rec=loader.load_store(str(UP/f'data/s200/{track}/row{row:03d}.json.gz'))
    pos,draws,diag=od.mixture_draws(rec,np.arange(5),5,n_total=20,seed_base=43_000_000)
    assert diag['exhausted_fallbacks']==0
    chosen=np.unique(np.linspace(0,len(pos)-1,min(24,len(pos))).astype(int))
    x=np.asarray(pos,float)[chosen];d=draws[chosen];K=5;n=20
    app=reconstruct(direct_record(x,d,rec['categories']),n,'cv',0)
    params,scores=base.cv.cv_select('M5a_segkernel',d,x,n,K,n_folds=5)
    assert app['parameters']==params
    counts=np.stack([np.bincount(v,minlength=K) for v in d])
    np.testing.assert_array_equal(app['raw'],counts/n)
    baseline=base.models.MODEL_REGISTRY['M5a_segkernel']();baseline.fit(x,counts,n,params)
    support=np.asarray(app['support'],float);pred=baseline.predict(support)
    e=err(app['smoothed'],pred);assert e==0
    score_error=abs(app['best_cv_score']-max(scores.values()));assert score_error==0
    expected=[{'left':int(x[e-1]),'right':int(x[e]),'midpoint':float((x[e-1]+x[e])/2)} for e in baseline.bkps[:-1]]
    assert app['boundaries']==expected
    # Independent algebra: prior + Gaussian-weighted counts; no cross-segment pooling.
    manual=np.empty_like(pred)
    for j,t in enumerate(support):
        segment=next(i for i,(lo,hi) in enumerate(baseline.seg_bounds_tok) if lo<t<=hi)
        a,b=baseline.seg_slices[segment];w=np.exp(-(t-x[a:b])**2/(2*params['h']**2))
        alpha=np.full(K,1/K)+w@counts[a:b];manual[j]=alpha/alpha.sum()
    me=err(pred,manual);assert me<1e-14
    add('released_data_live_vs_pristine_baseline',track=track,row=row,checkpoints=len(x),draws=n,
        parameters=params,cv_candidates=len(scores),cv_score_error=score_error,point_max_error=e,
        manual_kernel_max_error=me,boundaries=expected)

# Analytic segment likelihood, then exhaustive legal partitions vs PELT on a small example.
c=np.array([[9,1],[10,0],[9,1],[1,9],[0,10],[1,9]],float)
cost=MultinomialCost().fit(c)
for a in range(len(c)):
    for b in range(a+1,len(c)+1):
        pooled=c[a:b].sum(0);nz=pooled[pooled>0]
        assert abs(cost.error(a,b)-float(-(nz*np.log(nz/nz.sum())).sum()))<1e-12
pen=2.;partitions=[]
for size in range(0,len(c)):
    for cuts in itertools.combinations(range(1,len(c)),size):
        ends=(0,)+cuts+(len(c),)
        if min(np.diff(ends))<2:continue
        value=sum(cost.error(a,b) for a,b in zip(ends[:-1],ends[1:]))+pen*len(cuts)
        partitions.append((value,list(ends[1:])))
best=min(partitions)
m=MODEL_REGISTRY['M5a_segkernel']();m.fit(np.arange(len(c)),c,10,{'variant':'mult','pen':pen,'h':2.})
assert m.bkps==best[1]
add('multinomial_cost_and_exhaustive_pelt_check',breakpoints=m.bkps,objective=best[0],legal_partitions=len(partitions))

for run_id,key in [('edc9dbfd191f4edfa885c2e97116d021','pass_1'),('352516a7e5184bc6841d8eb075ecb09a','refinement')]:
    folder=ROOT/'live-runs'/run_id
    record=json.loads((folder/f'{key}.json').read_text());result=json.loads((folder/'result.json').read_text())
    saved=next(p for p in result['passes'] if p['id']==key)['curve']
    pos,draws=position_draws(record);n=draws.shape[1];recomputed=reconstruct(record,n,'cv',0)
    assert recomputed['parameters']==saved['parameters'];assert recomputed['boundaries']==saved['boundaries']
    for field in ['raw','smoothed','low','high']:
        assert err(saved[field],recomputed[field])<1e-14,(run_id,field)
    for b in record['branches']:
        assert b['answers']==[o['label'] for o in b['observations']]
        assert len(b['continuation_ids'])==len(b['answers'])==len(b['draw_indices'])
    per=[]
    for t,row in zip(pos,draws):
        obs=[o for b in record['branches'] if b['t']==t for o in b['observations']]
        labels={label:int(np.sum(row==i)) for i,label in enumerate(record['categories'])}
        per.append({'t':t,'labels':labels,'capped':sum(o['stop_reason']=='length' for o in obs)})
    masses=[p['retained_mass'] for p in record['positions']]
    add('saved_muse_curve_recomputes',run_id=run_id,draws=int(draws.size),positions=len(pos),
        parameters=saved['parameters'],boundaries=saved['boundaries'],max_numeric_error=err(saved['smoothed'],recomputed['smoothed']),
        retained_mass_min=min(masses),retained_mass_max=max(masses),per_checkpoint=per)

r1=json.loads((ROOT/'live-runs/edc9dbfd191f4edfa885c2e97116d021/pass_1.json').read_text())
r2=json.loads((ROOT/'live-runs/352516a7e5184bc6841d8eb075ecb09a/refinement.json').read_text())
assert r1['base']['gen_ids']==r2['base']['gen_ids'];assert r1['base']['prompt_ids']==r2['base']['prompt_ids']
add('saved_refinement_exact_source_ids',generated_tokens=len(r1['base']['gen_ids']),prompt_tokens=len(r1['base']['prompt_ids']))
path=Path(__file__).with_name('math-checks.json');path.write_text(json.dumps(report,indent=2)+'\n');print(path)
