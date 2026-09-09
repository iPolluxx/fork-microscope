"""Matched-budget comparison on released Llama S=200 stores (CPU, read-only).
Replicate blocks of S=30 draws: [0,30),[30,60),[60,90). Reference = weighted o_t over draws [90,200) (never used by any replicate).
Arms at stride s (budget = 2 grids x S=30):
  A_sep  : two offset grids (s, shift 1), fitted separately; report mean of the two TVs (what the tool shows today)
  A_avg  : average of the two separate fits (trivial combiner)
  A_joint: one fit on the union of both grids
  B_half : single uniform grid stride s/2, S=30
  C_dbl  : single grid stride s, S=60 (blocks [0,60),[30,90))
Metrics: mean TV over all positions; TV near reference jumps (thresh .15, radius 10)."""
import sys, json, numpy as np, importlib.util, os
os.environ.setdefault("OTRECON_FORCE_RUPTURES","1")
sys.path.insert(0, ".")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]/"vendor/forking-fast"
spec = importlib.util.spec_from_file_location("ldr", REPO/"data/loader.py"); ldr = importlib.util.module_from_spec(spec); spec.loader.exec_module(ldr)
from otrecon import data as od
from otrecon.models import MODEL_REGISTRY
from otrecon.metrics import tv_to_gt, gt_jumps, region_masks
P = {"variant":"mult","pen":64.0,"h":32.0}
def fit(x, counts, S):
    m = MODEL_REGISTRY["M5a_segkernel"](); m.fit(x.astype(float), counts, S, P); return m
def ref_complement(rec, lo):
    # weighted o_t over draws [lo:] per branch
    _, o = od.weighted_o_t(rec, lo, None); return o
rows = list(range(int(sys.argv[1]) if len(sys.argv)>1 else 30))
out = {}
# Reproduce reviewer settings; these arms are not exactly matched in expected tokens.
# Endpoint counts can also differ; retain actual budget diagnostics below.
budgets = {}
for row in rows:
    rec = ldr.load_store(str(REPO/f"data/s200/llama/row{row:03d}.json.gz"))
    pos, _ = od.weighted_o_t(rec)
    if pos != list(range(len(pos))): continue
    T = len(pos); ref = ref_complement(rec, 90)
    groups=od.branch_groups(rec)
    lengths=np.array([sum(w*np.mean(branch["cont_lens"]) for w,branch in zip(od.normalized_weights(groups[t]),groups[t])) for t in pos])
    _, draws, diag = od.mixture_draws(rec, np.arange(5), 5, n_total=90, seed_base=43_000_000)
    if diag["exhausted_fallbacks"]: continue
    jumps = gt_jumps(pos, ref, .15); prox, _ = region_masks(pos, jumps, 10)
    support = np.arange(T)
    def score(pred):
        tv = tv_to_gt(pred, ref); return float(tv.mean()), (float(tv[prox].mean()) if prox.any() else None)
    for s in (4, 8, 16):
        g1 = np.arange(0, T, s); g2 = g1 + 1; g2 = g2[g2 < T]
        if len(g1) < 4 or len(g2) < 4: continue
        half = np.arange(0, T, s//2); union = np.sort(np.concatenate([g1, g2]))
        budgets.setdefault(str(s),[]).append(dict(row=row,paired_draws=int(30*len(union)),uniform_draws=int(30*len(half)),doubled_draws=int(60*len(g1)),paired_expected_tokens=float(30*lengths[union].sum()),uniform_expected_tokens=float(30*lengths[half].sum()),doubled_expected_tokens=float(60*lengths[g1].sum())))
        res = {k: [] for k in ("A_sep","A_avg","A_joint","B_half","C_dbl")}
        for b in range(3):
            lo, hi = 30*b, 30*b+30
            c = lambda g, S=30, lo=lo: od.counts_from_draws(draws[g], 5, lo, lo+S)
            m1, m2 = fit(g1, c(g1), 30), fit(g2, c(g2), 30)
            p1, p2 = m1.predict(support), m2.predict(support)
            s1, s2 = score(p1), score(p2)
            res["A_sep"].append((float(np.mean([s1[0], s2[0]])), (float(np.mean([s1[1], s2[1]])) if None not in (s1[1], s2[1]) else None)))
            res["A_avg"].append(score((p1+p2)/2))
            res["A_joint"].append(score(fit(union, c(union), 30).predict(support)))
            res["B_half"].append(score(fit(half, c(half), 30).predict(support)))
        for lo in (0, 30):
            res["C_dbl"].append(score(fit(g1, od.counts_from_draws(draws[g1], 5, lo, lo+60), 60).predict(support)))
        out.setdefault(str(s), {}).setdefault("rows", []).append(row)
        for k, v in res.items():
            out[str(s)].setdefault(k, {"all": [], "jump": []})
            out[str(s)][k]["all"].append(float(np.mean([x[0] for x in v])))
            js = [x[1] for x in v if x[1] is not None]
            if js: out[str(s)][k]["jump"].append(float(np.mean(js)))
print("rows used per stride:", {s: len(v["rows"]) for s, v in out.items()})
for s, v in out.items():
    print(f"\n=== stride {s} (budget: 2 x {len(np.arange(0,300,int(s)))}-ish positions x S=30) ===")
    print(f"{'arm':8s} {'meanTV_all':>11s} {'sem':>7s} | {'meanTV_jump':>12s} {'sem':>7s} (n_jump_rows)")
    for k in ("A_sep","A_avg","A_joint","B_half","C_dbl"):
        a = np.array(v[k]["all"]); j = np.array(v[k]["jump"])
        print(f"{k:8s} {a.mean():11.4f} {a.std(ddof=1)/np.sqrt(len(a)):7.4f} | {j.mean():12.4f} {j.std(ddof=1)/np.sqrt(len(j)):7.4f} ({len(j)})")
    # paired differences vs the matched-budget uniform grid
    for k in ("A_sep","A_avg","A_joint","C_dbl"):
        d = np.array(v[k]["all"]) - np.array(v["B_half"]["all"])
        print(f"  paired {k}-B_half: mean {d.mean():+.4f}  sem {d.std(ddof=1)/np.sqrt(len(d)):.4f}  rows where {k} better: {(d<0).sum()}/{len(d)}")
destination=Path(sys.argv[2] if len(sys.argv)>2 else "/dev/null")
json.dump(dict(results=out,budgets=budgets,settings=dict(rows_requested=len(rows),samples=30,strides=[4,8,16],parameters=P,reference_branch_slice=[90,200],mixture_seed=43000000,source_commit="d32fed8d4162a4888291c4b3a38b059727c85a41"),limitations=["Reviewer reproduction, not an exactly matched-token-budget comparison.","All positions scored, including extrapolation beyond each arm's outer observations.","Three S=30 blocks; S=60 arm uses two overlapping blocks. Row-level comparisons are the unit of aggregation.","Reference uses disjoint per-branch draws 90:200; outcome categories are all five.","One released model, fixed hyperparameters, no GPU generation or adaptive arm."]),destination.open('w'),indent=2)
