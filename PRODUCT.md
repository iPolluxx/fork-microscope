# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: working mechanistic-interpretability researchers who attach their own model worker (local machine or a disposable GPU VM such as RunPod) and run checkpoint scans on their own prompts. They are here for hours of instrument use, not a five-minute browse. They already understand sampling, temperature, top-k, and cross-validation; they do not need the concepts explained, they need the settings exposed and the evidence retrievable.

Secondary (unconfirmed, do not design for by default): reviewers opening a link from a public writeup who never attach a worker.

## Product Purpose

A local model-sampling workbench around Goodfire's Forking Fast. Generate a fixed response, sample continuations at selected checkpoints, inspect the actual completions, and reconstruct answer-outcome curves over response-token position. Success is a researcher running their own prompt set on their own model and getting evidence they can inspect and export — not a benchmark number.

## Positioning

Configurable passes on any prompt. Upstream Forking Fast provides a sampling library and a released-data explorer. Fork Microscope connects them to a live workflow that lets a researcher write free-form prompts, track 1–32 answer texts, and run up to eight independently fitted sampling passes (own region, spacing, offset, draws per checkpoint, seed) against the same fixed trace. A notebook can plot; this is the instrument with the knobs on the front.

## Operating Context

- Workflow: **Workspace → Configure → Explore → Compare**. Save prompt sets, run selected prompts sequentially on one attached model, explore saved runs, compare compatible saved evidence.
- Deployment split: a static dashboard (`dist/dashboard/`, built by `scripts/build_dashboard.py`) plus an independently owned worker (`fork-microscope serve --port 8767`). One private worker per user or trusted team; never a shared multi-tenant inference API. Hosted-to-local connection uses a worker token and an exact allowed origin.
- Dev entry: `.venv/bin/fork-microscope serve --port 8767`, open `http://127.0.0.1:8767/`. Root serves the workspace; `/observatory.html`, `/compare.html`, `/live.html` are the other surfaces; `/index.html` is the legacy two-pass replay.
- Models: Hugging Face IDs or local Transformers directories. Muse-Glimmer-30B (image-text-to-text) and generic causal LMs. Custom remote code disabled. CPU execution available for small models; real work is GPU (A100 80GB class for Muse).
- Storage: prompt sets, jobs, and saved evidence live on the worker (`live-runs/`, `workspace-data/`). Export/import evidence as JSON archives (≤64 MB in browser). Disposable VMs mean "back up before deleting" is a real, recurring user moment.
- Evaluation rituals: `fork-microscope doctor` / `doctor --muse` preflight; Python + JS test suites; VALIDATION.md records every run with its caveats.

## Capabilities and Constraints

- Schema 2 data point: at checkpoint t, retain the prompt plus response tokens before t; enumerate retained next-token branches by recorded temperature-1 probability; S = total draws per checkpoint (not per branch); every generated outcome used exactly once.
- Reconstruction: Goodfire's M5a segment-kernel estimator, fixed penalty 64 / bandwidth 32, five-fold cross-validation. Nominal 90% bands are model-based with no guaranteed frequentist coverage. Fits and reference metrics are withheld when completion/short-grid gates fail.
- Answer matching: NFKC + case + whitespace normalized whole-phrase mention matching; multiple/none/capped → `Other` (reserved). Not a correctness judgment; not semantic.
- Passes: 1 default, up to 8; independent settings and fits; a second pass is optional, not a recommended advantage.
- Terminology in use: trace, checkpoint, pass, draw, branch, continuation, reconstruction, reference (dense), prompt set, batch, worker, evidence.
- Technical: vanilla HTML/CSS/ES modules, Plotly for plots, no build framework; Python 3.13 / uv / Transformers backend; server binds loopback and checks Host/Origin.
- Measurement stance (factual, not a voice rule): these are behavioral measurements, not evidence of an internal reasoning mechanism; a smaller token allowance is not matched-accuracy savings.

**Explicitly not binding (user declined to pin these on 2026-09-10):** the current name/tagline/✳ mark presentation; the current caveat copy wording (facts above must stay true, but phrasing and placement are open); and the guarantee that saved evidence is browsable with no worker attached. Later work may change these with the user's sign-off.

## Brand Commitments

- **Goodfire / Forking Fast attribution stays user-visible** in the interface itself — including the upstream revision hashes where evidence derives from them — not buried in THIRD-PARTY.md. This is the one binding identity constraint.

## Evidence on Hand

- Real saved runs under `live-runs/` and `outputs/` (CPU runs `8efc8894…`, `292a1524…`; Llama-3-8B-Instruct tinyMMLU replay, revision `d32fed8`).
- Reviewer-provided 40-question Llama replay benchmark reproduction in `reports/`; public workflow report at `reports/public-workflow/README.md`.
- VALIDATION.md: dated validation log with explicit "not yet validated" items (CUDA acceptance, full Muse weights, peak memory, throughput).
- Absent — do not fabricate: user testimonials, adoption numbers, matched-accuracy savings claims, GPU runtime savings, research-quality Muse results, pricing/quota figures.

## Product Principles

1. Knobs on the front, receipts behind every number: every setting a researcher would want to vary is exposed, and every plotted value can be traced to the literal continuations that produced it.
2. The worker is theirs: the product never assumes central compute, accounts, or shared data; design around disposable machines and portable exports.
3. Say exactly what was measured, no more: withheld fits, `Other`, and gate failures are first-class states, not error edge cases.
4. Independent passes, one trace: comparisons never blend passes; the UI must keep them visually and semantically separate.
5. Credit upstream in the product: Goodfire's method and revisions are named where the evidence appears.
