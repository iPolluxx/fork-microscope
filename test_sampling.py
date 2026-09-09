import json
from types import SimpleNamespace
import numpy as np
import pytest
from sampling import pass_plan, allocation, position_draws
from live_service import reconstruct, LiveService
from outcome_readout import inspect_continuation, muse_answer

CONFIG=dict(passes=[dict(id='pass_1',label='Pass 1',start=0,end=15,stride=4,offset=0,samples=10,seed=0)],cont_max=8,temperature=1,top_k=2,threshold=.05,dense=False,reference_samples=10,tuning='cv')

def test_one_pass_and_independent_offsets():
    assert pass_plan(CONFIG,20)[0]['positions']==[0,4,8,12]
    second=CONFIG['passes'][0]|dict(id='pass_2',offset=1,stride=3,end=17)
    plan=pass_plan(CONFIG|dict(passes=CONFIG['passes']+[second]),20)
    assert plan[1]['positions']==[1,4,7,10,13,16]
    for key,value in [('id','../x'),('offset',4),('samples',True),('end',100)]:
        with pytest.raises(ValueError):pass_plan(CONFIG|dict(passes=[CONFIG['passes'][0]|{key:value}]),20)
    with pytest.raises(ValueError):pass_plan(CONFIG|dict(passes=CONFIG['passes']*2),20)
    with pytest.raises(ValueError):pass_plan(CONFIG|dict(passes=[]),20)

def test_branch_allocation_is_weighted_and_repeatable():
    branches=[SimpleNamespace(tok_p=.6),SimpleNamespace(tok_p=.4)]
    a=allocation(branches,10000,[1,2,3])
    assert a==allocation(branches,10000,[1,2,3])
    assert abs(a.count(0)/len(a)-.6)<.02

def mixture_record(cap_hits=0):
    r=dict(sampling_design='position_mixture_v1',categories=['A','B','C','D','Other'],
        base={'finish_reason':'stop'},config={'cont_temperature':1},positions=[],branches=[])
    for t in [0,4,8,12]:
        r['positions'].append(dict(t=t,samples=10,retained_mass=1))
        for tok,indices,label in [(1,[0,2,4,6,8,9],'A'),(2,[1,3,5,7],'B')]:
            r['branches'].append(dict(t=t,tok_id=tok,answers=[label]*len(indices),draw_indices=indices,
                observations=[dict(stop_reason='length' if i<cap_hits else 'eos') for i in indices]))
    return r

def test_every_collected_outcome_is_used_once_in_fit():
    r=mixture_record();pos,draws=position_draws(r)
    assert draws.shape==(4,10)
    f=reconstruct(r,10,'cv',123)
    np.testing.assert_allclose(f['raw'],[[.6,.4,0,0,0]]*4)
    assert f['raw']==f['weighted']
    assert f['mixture_diagnostics']['all_collected_draws_used']
    assert f['cv_candidates']>0
    r['branches'][0]['draw_indices'][0]=2
    with pytest.raises(ValueError,match='Duplicate'):position_draws(r)

def test_completion_gate_and_short_grid_not_misleading():
    r=mixture_record(cap_hits=2)
    f=reconstruct(r,10,'cv',123)
    assert f['fit_status']=='withheld' and f['support']==[] and f['parameters'] is None
    r=mixture_record();r['positions']=r['positions'][:2];r['branches']=r['branches'][:4]
    f=reconstruct(r,10,'cv',123)
    assert f['tuning']=='fixed' and f['cv_candidates']==0 and not f['boundaries']

def test_generic_cap_cannot_become_a_confident_answer():
    tok=SimpleNamespace(decode=lambda *a,**k:'The answer is (A)')
    model=SimpleNamespace(tokenizer=tok,eos_ids=[99],is_muse=False)
    base=SimpleNamespace(gen_ids=[1]);branch=SimpleNamespace(idx=0,tok_id=2)
    capped=inspect_continuation(model,base,branch,[1,2],2)
    assert capped['label']=='Other' and capped['label_source']=='incomplete'
    completed=inspect_continuation(model,base,branch,[1],2)
    assert completed['label']=='A' and completed['label_source']=='completed_regex'

def test_muse_alternate_eos_and_incomplete_reply():
    assert muse_answer('to=user<|message|>The answer is (B)<|end_of_text|>')=='B'
    model=SimpleNamespace(tokenizer=SimpleNamespace(decode=lambda *a,**k:'to=user<|message|>The answer is (B)'),eos_ids=[99],is_muse=True)
    base=SimpleNamespace(gen_ids=[1]);branch=SimpleNamespace(idx=0,tok_id=2)
    assert inspect_continuation(model,base,branch,[1,2],2)['label']=='Other'
    assert inspect_continuation(model,base,branch,[1],2)['label']=='B'

def test_multibranch_collection_roundtrip(tmp_path,monkeypatch):
    import live_service as module
    from forking_paths.model import BasePath
    monkeypatch.setattr(module,'RUNS',tmp_path)
    class Tokenizer:
        def decode(self,ids,**kwargs):return 'The answer is (A)' if ids[-1]==7 else 'The answer is (B)'
    calls=[]
    class Model:
        eos_ids=[99];is_muse=False;tokenizer=Tokenizer()
        info={'context_limit':1000,'model_id':'fixture','vocab_size':20}
        model=SimpleNamespace(generation_config=SimpleNamespace(to_dict=lambda:{}))
        def decode(self,ids):return self.tokenizer.decode(ids)
        def draw_branch(self,branch,count,cap,temp,seed,check):
            calls.append(count);return [[7 if branch.tok_id==10 else 8]]*count
    s=LiveService();s.model=Model();s.base=BasePath([1],[10]*16,[[10,11]]*16,[[np.log(.6),np.log(.4)]]*16,'stop')
    s.question={'question':'fixture','choices':['a','b','c','d']};s.base_config={'max_tokens':16};s.job={'id':'a'*32}
    s.collect(CONFIG|{'dense':True})
    r=s.result('a'*32,raw=True)
    assert sum(calls)==170 # 4*10 + 13*10 reference
    assert len(r['passes'])==1 and r['schema_version']==2
    assert r['measured']['pass_1']['continuations']==40
    assert r['passes'][0]['curve']['comparison']['compared_positions']==13
    for key in ['pass_1','dense']:
        rec=r['records'][key];_,draws=position_draws(rec)
        assert draws.size==sum(len(b['answers']) for b in rec['branches'])
        assert all(b['observations'][0]['full_response_text'] for b in rec['branches'])


def test_dashboard_module_is_served_and_root_opens_live_workspace():
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer
    from microscope_server import Handler
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        url=f'http://127.0.0.1:{server.server_port}'
        with urllib.request.urlopen(url+'/passes.mjs') as response:
            assert response.status==200 and b'export function newPass' in response.read()
        with urllib.request.urlopen(url+'/') as response:
            html=response.read()
            assert b'id="add-pass"' in html and b'id="continuations"' in html
        request=urllib.request.Request(url+'/api/live/run',data=b'{}',headers={'Content-Type':'application/json','Origin':url})
        with pytest.raises(urllib.error.HTTPError) as exc: urllib.request.urlopen(request)
        assert exc.value.code==400
    finally:
        server.shutdown();server.server_close();thread.join()
