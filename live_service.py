"""One attached model, cancellable collection jobs, and auditable saved results."""
from __future__ import annotations
import gc
import importlib.metadata
import json
import math
from pathlib import Path
import threading
import time
import uuid
import numpy as np
from forking_paths.config import ForkingConfig
from forking_paths.resample import enumerate_branches_at
from otrecon import data as od
from otrecon.cv import cv_select
from otrecon.models import MODEL_REGISTRY
from sampling import pass_plan, allocation, position_draws
from otrecon.metrics import tv_to_gt, band_coverage, heldout_loglik

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "live-runs"
CATS = ["A", "B", "C", "D", "Other"]


def integer(value, name, lo, hi):
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f"{name} must be a whole number from {lo} to {hi}.")
    return value


def real(value, name, lo, hi):
    if type(value) not in (float, int) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f"{name} must be between {lo} and {hi}.")
    return value


def exact(obj, fields):
    if type(obj) is not dict or set(obj) != set(fields.split()):
        raise ValueError("Unexpected or missing fields.")


def grid_plan(c, last):
    plan = pass_plan(c, last)
    grids = {p['id']:p['positions'] for p in plan}
    grids['dense'] = list(range(min(p['positions'][0] for p in plan), max(p['positions'][-1] for p in plan)+1))
    return grids


def reconstruct(record, n, tuning, seed):
    warnings = []
    if record.get('sampling_design') == 'position_mixture_v1':
        positions, draws = position_draws(record)
        idxs = positions
        if draws.shape != (len(positions), n): raise ValueError("Saved draw count differs from requested reconstruction count.")
        weighted = od.counts_from_draws(draws,5,0,n)/n
        diag = dict(n_total=n,n_positions=len(positions),exhausted_fallbacks=0,all_collected_draws_used=True)
        capped = sum(o['stop_reason']=='length' for b in record['branches'] for o in b['observations'])
        total = draws.size
        unparsed=sum(o.get('label')=='Other' and o['stop_reason']!='length' for b in record['branches'] for o in b['observations'])
        if unparsed: warnings.append(f'{unparsed}/{total} completed continuations have no parsed answer; Other is not an answer choice.')
        if capped/total > .1:
            warnings.append(f'{capped}/{total} continuations reached the token cap. Reconstruction withheld; increase the cap.')
        if record['base'].get('finish_reason') != 'stop':
            warnings.append('The fixed base response did not finish. Inspect it before interpreting outcomes.')
        if n < 20: warnings.append('Fewer than 20 draws per checkpoint: this is a small-sample diagnostic, not a reliability guarantee.')
        masses = [p['retained_mass'] for p in record['positions']]
        if min(masses)<.95: warnings.append('Some checkpoints retain less than 95% of next-token probability mass; omitted branches are excluded.')
        if record['config'].get('cont_temperature',1)!=1:
            warnings.append('Branch weights use temperature 1; continuation temperature differs.')
        if capped/total > .1:
            return dict(positions=positions,weighted=weighted.tolist(),raw=weighted.tolist(),support=[],smoothed=[],low=[],high=[],boundaries=[],parameters=None,tuning='withheld',cv_candidates=0,best_cv_score=None,mixture_diagnostics=diag,warnings=warnings,fit_status='withheld')
    else:
        idxs, weighted = od.weighted_o_t(record)
        positions, draws, diag = od.mixture_draws(record, np.arange(5), 5, n_total=n, seed_base=seed)
        if diag['exhausted_fallbacks']: raise RuntimeError('Mixture sampling exhausted a branch unexpectedly.')
        warnings.append('Legacy per-branch record: the fit uses a subsample; weighted markers use all branch observations.')
    if len(positions)<4:
        warnings.append('Fewer than four checkpoints: segmentation and cross-validation are disabled; fixed smoothing only.')
        tuning='fixed'
    x = np.asarray(positions, float)
    params, scores = (cv_select("M5a_segkernel", draws, x, n, 5, n_folds=5)
        if tuning == "cv" else ({"variant":"mult", "pen":64.0, "h":32.0}, {}))
    counts = od.counts_from_draws(draws, 5, 0, n)
    model = MODEL_REGISTRY["M5a_segkernel"]()
    model.fit(x, counts, n, params)
    support = np.arange(positions[0], positions[-1]+1)
    pred = model.predict(support.astype(float))
    low, high = model.credible_band(support.astype(float), .9)
    if not np.isfinite(pred).all() or not np.allclose(pred.sum(axis=1), 1):
        raise RuntimeError("Invalid reconstruction probabilities.")
    boundaries = [dict(left=positions[e-1], right=positions[e], midpoint=(positions[e-1]+positions[e])/2)
        for e in model.bkps[:-1]]
    return dict(positions=idxs, weighted=weighted.tolist(), raw=(counts/n).tolist(),
        support=support.tolist(), smoothed=pred.tolist(), low=low.tolist(), high=high.tolist(),
        boundaries=boundaries, parameters=params, tuning=tuning,
        cv_candidates=len(scores), best_cv_score=max(scores.values()) if scores else None,
        mixture_diagnostics=diag,warnings=warnings,fit_status='complete')


def compare(reference, curve, samples, seed):
    if reference.get('sampling_design') == 'position_mixture_v1':
        positions, draws = position_draws(reference)
        weighted = od.counts_from_draws(draws,5,0,samples)/samples
    else:
        positions, weighted = od.weighted_o_t(reference)
        _, draws, _ = od.mixture_draws(reference, np.arange(5), 5, n_total=samples, seed_base=seed)
    ix = np.array([positions.index(t) for t in curve["support"]])
    pred = np.asarray(curve["smoothed"])
    return dict(mean_tv=float(tv_to_gt(pred, weighted[ix]).mean()),
        mean_log_likelihood=heldout_loglik(pred, draws[ix], 0),
        empirical_band_coverage=float(band_coverage(np.asarray(curve["low"]),np.asarray(curve["high"]),weighted[ix]).mean()),
        compared_positions=len(ix))


class Cancelled(Exception):
    pass


class LiveService:
    def __init__(self):
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.model = self.base = self.question = None
        self.job = dict(status="idle", phase="Attach an open-weight model to begin.", completed=0, total=0)
        self.base_config = None
        RUNS.mkdir(exist_ok=True)

    def status(self):
        with self.lock:
            return dict(job=dict(self.job), model=self.model.info if self.model else None,
                base=self.base_metadata() if self.base else None)

    def base_metadata(self):
        return dict(question=self.question, text=self.model.decode(self.base.gen_ids),
            tokens=[self.model.tokenizer.decode([x]) for x in self.base.gen_ids],
            length=len(self.base.gen_ids), finish_reason=self.base.finish_reason,
            config=self.base_config, top_token_probabilities=[float(np.exp(x[0])) for x in self.base.topk_logprobs])

    def progress(self, phase, completed=0, total=0):
        with self.lock:
            self.job.update(phase=phase, completed=completed, total=total)

    def check(self):
        if self.stop.is_set():
            raise Cancelled()

    def start(self, action, payload):
        with self.lock:
            if self.job["status"] == "running":
                raise ValueError("A job is already running. Wait or stop it first.")
            if action not in ("load", "base", "run", "unload"):
                raise ValueError("Unknown action.")
            # Validate synchronously before launching jobs.
            if action == "load":
                exact(payload, "model_id revision device batch_size")
                for key in ("model_id", "revision"):
                    if not isinstance(payload[key], str) or not payload[key].strip() or len(payload[key])>500:
                        raise ValueError("Enter a model ID/path and revision.")
                if payload["device"] not in ("auto", "cpu", "cuda"):
                    raise ValueError("Choose auto, CPU or CUDA.")
                integer(payload["batch_size"], "Batch size", 1, 128)
            elif action == "base":
                if not self.model: raise ValueError("Attach a model first.")
                exact(payload, "question choices mode max_tokens seed")
                if not isinstance(payload["question"], str) or not 1<=len(payload["question"].strip())<=16000:
                    raise ValueError("Enter a question (up to 16,000 characters).")
                if type(payload["choices"]) is not list or len(payload["choices"]) != 4 or any(not isinstance(x,str) or not x.strip() or len(x)>4000 for x in payload["choices"]):
                    raise ValueError("Enter four nonempty answer choices.")
                if payload["mode"] not in ("chat", "base"): raise ValueError("Choose chat or base mode.")
                integer(payload["max_tokens"], "Base cap", 8, 4096)
                integer(payload["seed"], "Seed", 0, 2**31-1)
            elif action == "run":
                self.estimate(payload)  # Checks base, complete config and context allowance.
            else:
                exact(payload, "")
            self.stop.clear()
            self.job = dict(id=uuid.uuid4().hex, status="running", action=action,
                phase=f"Starting {action}…", completed=0,total=0, started=time.time())
            job_id = self.job["id"]
            threading.Thread(target=self._execute, args=(action,payload), daemon=True).start()
            return dict(job_id=job_id)

    def _execute(self, action, p):
        try:
            if action in ("unload", "load"):
                self.base = self.question = self.base_config = None
                self.model = None
                gc.collect()
                import torch
                if torch.cuda.is_available(): torch.cuda.empty_cache()
                if action == "load":
                    from live_model import AttachedModel
                    self.progress("Loading tokenizer and weights…")
                    self.model = AttachedModel(p["model_id"],p["revision"],p["device"],p["batch_size"])
                    self.check()
            elif action == "base":
                self.progress("Generating the greedy base response and recording next-token probabilities…")
                ids = self.model.prompt(p["question"], p["choices"], p["mode"])
                self.context_check(len(ids)+p["max_tokens"])
                base = self.model.base_path(ids, p["max_tokens"], top_k=min(50,self.model.info["vocab_size"]), seed=p["seed"])
                self.check()
                if len(base.gen_ids) < 2: raise ValueError("The model produced fewer than two response tokens. Try another question.")
                self.base,self.question,self.base_config = base,dict(question=p["question"],choices=p["choices"]),p
            else:
                self.collect(p)
            with self.lock:
                self.job.update(status="complete",phase=f"{action.capitalize()} complete",finished=time.time())
                if action == "run": self.job["completed"]=self.job["total"]
        except Cancelled:
            with self.lock: self.job.update(status="cancelled",phase="Stopped at a sampling boundary. Any saved partial collection is retained.",finished=time.time())
        except Exception as exc:
            with self.lock: self.job.update(status="error",phase=str(exc)[:1500],finished=time.time())

    def context_check(self, needed):
        limit = self.model.info["context_limit"]
        if limit and needed > limit:
            raise ValueError(f"This configuration needs up to {needed} context tokens; the model limit is {limit}. Reduce token caps.")

    def configuration(self, c):
        cfg = ForkingConfig(top_k=c["top_k"],p_thresh=c["threshold"],n_samples=c.get("samples",5),
            n0_samples=c.get("samples",5),tok_depth=len(self.base.gen_ids),cont_max_tokens=c["cont_max"],
            base_max_tokens=self.base_config["max_tokens"] if self.base_config else len(self.base.gen_ids),
            cont_temperature=c["temperature"],seed=c.get("seed",0))
        return cfg

    def branches(self, cfg, positions):
        # The base records the top 50 once; apply the user's top-k before upstream enumeration.
        from dataclasses import replace
        base = replace(self.base,topk_ids=[x[:cfg.top_k] for x in self.base.topk_ids],
            topk_logprobs=[x[:cfg.top_k] for x in self.base.topk_logprobs])
        return enumerate_branches_at(base, cfg, positions)

    def estimate(self, c):
        if not self.base or not self.model: raise ValueError("Generate a base response first.")
        plan = pass_plan(c,len(self.base.gen_ids)-1)
        grids = grid_plan(c,len(self.base.gen_ids)-1)
        self.context_check(len(self.base.prompt_ids)+max(grids['dense'])+1+c['cont_max'])
        cfg = self.configuration(c)
        counts = {key:len(self.branches(cfg,pos)) for key,pos in grids.items()}
        combined = sum(len(p['positions'])*p['samples'] for p in plan)
        reference = len(grids['dense'])*c['reference_samples'] if c['dense'] else 0
        return dict(grids=grids,passes=plan,branches=counts,combined_rollouts=combined,
            reference_rollouts=reference,total_rollouts=combined+reference,
            max_continuation_tokens=(combined+reference)*c['cont_max'],
            sampled_checkpoint_visits=sum(len(p['positions']) for p in plan),
            unique_checkpoints=len(set(t for p in plan for t in p['positions'])),
            dense_positions=len(grids['dense']),sampling_design='position_mixture_v1')

    def record(self, cfg):
        return dict(meta=dict(row_id=0,**self.question,model=self.model.info["model_id"]),
            categories=CATS,base=dict(gen_ids=self.base.gen_ids,prompt_ids=self.base.prompt_ids,
            base_text=self.model.decode(self.base.gen_ids),token_texts=[self.model.tokenizer.decode([x]) for x in self.base.gen_ids],
            finish_reason=self.base.finish_reason),config=cfg.to_dict(),branches=[])

    def collect(self, c):
        from outcome_readout import inspect_continuation
        estimate = self.estimate(c)
        cfg = self.configuration(c)
        run_id = self.job['id']; folder = RUNS/run_id; folder.mkdir()
        records,curves,phase_costs = {},{},{}
        done=0; total=estimate['total_rollouts']
        metadata = dict(id=run_id,schema_version=2,sampling_design='position_mixture_v1',model=self.model.info,
            settings=c,base_config=self.base_config,estimate=estimate,created=time.time(),
            upstream_commit='d32fed8d4162a4888291c4b3a38b059727c85a41',
            generation_defaults=self.model.model.generation_config.to_dict(),
            effective_sampling=dict(branch_temperature=1,continuation_temperature=c['temperature'],top_p=1,top_k=0),
            versions={p:importlib.metadata.version(p) for p in ['torch','transformers','otrecon','forking-paths']})
        self.save(folder/'manifest.json',metadata)
        plans=list(estimate['passes'])
        if c['dense']:
            plans.append(dict(id='dense',label='Independent reference',positions=estimate['grids']['dense'],samples=c['reference_samples'],seed=0))
        for phase_i,p in enumerate(plans):
            key=p['id']; n=p['samples']; record=self.record(cfg)
            record.update(sampling_design='position_mixture_v1',positions=[])
            record['config'].update(n_samples=n,n0_samples=n)
            started=time.perf_counter(); generated=0
            for t in p['positions']:
                self.check()
                branches=self.branches(cfg,[t])
                selection_seed=[p['seed'],phase_i,t,101]
                picks=allocation(branches,n,selection_seed)
                record['positions'].append(dict(t=t,samples=n,retained_mass=float(sum(b.tok_p for b in branches)),
                    selection_seed=selection_seed,branch_choices=picks,candidates=[dict(tok_id=b.tok_id,tok_p=b.tok_p,is_base=b.is_base) for b in branches]))
                for bi,branch in enumerate(branches):
                    indices=[i for i,v in enumerate(picks) if v==bi]
                    if not indices: continue
                    self.progress(f"{p['label']} · token {t} · {len(indices)} draws from branch {bi+1}",done,total)
                    seed=int(np.random.SeedSequence([p['seed'],phase_i,t,branch.tok_id,202]).generate_state(1)[0])
                    continuations=self.model.draw_branch(branch,len(indices),c['cont_max'],c['temperature'],seed,self.check)
                    if len(continuations)!=len(indices): raise RuntimeError('Model returned an incorrect draw count.')
                    observations=[inspect_continuation(self.model,self.base,branch,cont,c['cont_max']) for cont in continuations]
                    generated+=sum(map(len,continuations))
                    record['branches'].append(dict(t=t,tok_id=branch.tok_id,tok_p=branch.tok_p,is_base=branch.is_base,
                        answers=[o['label'] for o in observations],draw_indices=indices,cont_lens=list(map(len,continuations)),
                        continuation_ids=continuations,observations=observations,seed=seed))
                    done+=len(indices)
                    self.save(folder/f'{key}.json',record)
            records[key]=record
            obs=[o for b in record['branches'] for o in b['observations']]
            phase_costs[key]=dict(continuations=len(obs),continuation_tokens=generated,wall_seconds=time.perf_counter()-started,
                logit_fallback=0,at_continuation_cap=sum(o['stop_reason']=='length' for o in obs),
                unresolved=sum(o.get('label')=='Other' for o in obs))
            if key!='dense':
                self.progress(f"Reconstructing {p['label']}…",done,total)
                curves[key]=reconstruct(record,n,c['tuning'],43_000_000+phase_i)
                self.check()
        reference=None
        if c['dense']:
            pos,draws=position_draws(records['dense'])
            values=od.counts_from_draws(draws,5,0,c['reference_samples'])/c['reference_samples']
            rm=phase_costs['dense']; valid=rm['at_continuation_cap']/rm['continuations']<=.1
            reference=dict(positions=pos,values=values.tolist(),independent=True,valid=valid,
                warning=None if valid else 'Reference exceeds 10% cap hits; comparison metrics withheld.')
            for key in curves:
                if valid and curves[key]['fit_status']=='complete':
                    curves[key]['comparison']=compare(records['dense'],curves[key],c['reference_samples'],44_000_000)
        result=dict(**metadata,base=self.base_metadata(),categories=CATS,
            passes=[dict(id=p['id'],label=p['label'],configuration=p,curve=curves[p['id']]) for p in estimate['passes']],
            reference=reference,measured=phase_costs,caveats=[
                'Every generated draw is used once. Branches are chosen from their renormalized temperature-1 probabilities.',
                'Omitted branch mass is excluded; these are truncated-mixture outcome estimates.',
                'Fits are withheld above 10% cap hits. This is a diagnostic gate, not a statistical guarantee.',
                'Nominal bands are model-based, may under-cover, and exclude exactly zero and one.',
                'Passes are fitted independently; overlapping checkpoints cost additional independent draws.',
                'No claim of reasoning mechanism, exhaustive fork detection, or matched-accuracy savings.'])
        self.save(folder/'result.json',result)
        with self.lock: self.job['result_id']=run_id

    @staticmethod
    def save(path, data):
        temp=path.with_suffix(".tmp")
        temp.write_text(json.dumps(data,allow_nan=False),encoding="utf-8")
        temp.replace(path)

    def cancel(self):
        self.stop.set()
        return {"stopping":self.job["status"]=="running"}

    def results(self):
        entries=[]
        for file in sorted(RUNS.glob("*/result.json"),key=lambda p:p.stat().st_mtime,reverse=True)[:100]:
            value=json.loads((file.parent/"manifest.json").read_text())
            entries.append(dict(id=value["id"],model=value["model"]["model_id"],created=value["created"]))
        return entries

    def result(self, run_id, raw=False):
        if len(run_id)!=32 or any(x not in "0123456789abcdef" for x in run_id): raise ValueError("Invalid run ID.")
        folder=RUNS/run_id
        file=folder/"result.json"
        if not file.exists(): raise ValueError("No completed result exists for this run.")
        result=json.loads(file.read_text())
        if raw:
            result["records"]={p.stem:json.loads(p.read_text()) for p in folder.glob("*.json") if p.stem not in ("result","manifest")}
        return result
