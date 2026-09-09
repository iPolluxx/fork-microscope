# Fork microscope

A local model-sampling workbench around Goodfire's Forking Fast. Generate a fixed response, sample continuations at selected checkpoints, inspect the actual completions, and reconstruct answer-outcome curves. These are behavioral measurements, not proof of an internal reasoning mechanism.

The dashboard starts with **one pass**. Add up to eight passes using the tabs. Each pass has its own name, region, spacing, offset, total draws per checkpoint, and random seed. Passes use the same fixed trace and are fitted independently. A second pass is optional, not a recommended sampling advantage.

## Start locally or on a GPU VM

Use a recursive clone and keep the checkout together: this is not a standalone wheel distribution.

```bash
git clone --recurse-submodules https://github.com/iPolluxx/fork-microscope.git
cd fork-microscope
./scripts/setup.sh cuda
.venv/bin/fork-microscope doctor --muse
.venv/bin/fork-microscope serve --port 8767
```

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/) first. Authenticate GitHub yourself when cloning the private repository. On an existing checkout after an update, rerun setup (or reinstall the editable package with `uv pip install --python .venv/bin/python --no-deps --editable .` when dependencies did not change).

For a remote VM, run on your computer (substitute the real exposed SSH port and address):

```bash
ssh -N -L 8767:127.0.0.1:8767 -p SSH_PORT USER@VM_HOST
```

Open **http://127.0.0.1:8767/**. The root now opens the live workspace. The older two-grid recorded-data demo remains at `/index.html` and is labeled as legacy. The server binds loopback and checks the Host/Origin; keep local and remote dashboard ports identical. Do not expose the model-control API directly to the internet.

The [Docker instructions](docker/README.md) describe a prebuilt environment and optional automatic Muse loading. The image-publishing workflow has not been dispatched, and container-based GPU inference remains untested.

## Hardware and model support

The earlier short Muse-Glimmer-30B test ran successfully in full BF16 on one A100 80GB, at batch size one. Observed sampling memory was about 56GiB, not a peak-memory benchmark. Larger batches and contexts need new measurements. Start with 200GB disk for weights, environment and results, and an NVIDIA driver compatible with CUDA 12.8. Put results and the model cache on persistent storage if desired; otherwise copy results home before stopping a disposable Pod.

Muse is pinned in `configs/muse-smoke.json` to `meta-models/Muse-Glimmer-30B` revision `a4e59da52a7bc87ae7251dd5545c0dd437c44b68`. `doctor --muse` checks configuration, processor, template and an empty-weight architecture; it does not load full model weights.

The loader accepts a supported Hugging Face model ID or complete Transformers directory on the server machine. Muse uses AutoModelForImageTextToText; generic models use AutoModelForCausalLM. Custom remote code is disabled. This is not a GGUF/Ollama loader or a promise of arbitrary architecture support. Colab does not connect automatically.

## What a data point means (schema 2)

At checkpoint t, retain the prompt plus response tokens before t. Enumerate retained next-token branches using the recorded temperature-1 probabilities, top-k setting and minimum branch probability (the base token is always retained). Normalize over retained branches; omitted mass is excluded and saved for inspection.

For each of S draws at that checkpoint, choose a branch by its normalized probability BEFORE generating its continuation. Group draws by branch for execution, but save their original mixture order. Every generated outcome is used exactly once in the histogram and in the reconstruction input. **S means total draws per checkpoint, not draws per branch.** Increasing retained branch count does not multiply the draw budget.

A marker is the frequency of each observed answer among those S draws. Goodfire's M5a segment-kernel estimator is fitted to those same multinomial counts. Cross-validation uses those same draw sequences; there is no second subsampling step. Nominal 90% bands are model-based, exclude exactly 0 and 1, and have no guaranteed frequentist coverage.

Continuations use the chosen temperature, top_p=1 and top_k=0. Branch-selection probabilities always use temperature 1; the UI warns when the continuation temperature differs. Inherited generation defaults and effective sampling settings are saved separately.

New runs use strict completed-answer extraction. A capped output is Other even if it contains an apparent answer. Generic models parse completed response text with the upstream answer regex and do not force an A-D logit fallback. Muse only parses a completed `to=user` channel; both `<|eot|>` and `<|end_of_text|>` stop generation, while `<|eom|>` only ends a channel. Upstream strips the terminal EOS, so stop reason is inferred from the forced token or stripped length and the exact removed EOS identity is not fabricated.

## Inspect and interpret

Click an observed point or use the continuation viewer's pass/checkpoint selectors. New records contain decoded full-response and continuation text, label source, channel reached, stop reason/evidence, IDs, branch probabilities and original draw indices. Model text is rendered literally, not interpreted as instructions or HTML.

- Above 10% continuation-cap hits, reconstruction and comparison metrics are withheld; the actual outcome markers and text remain visible. This is an engineering diagnostic gate, not a scientific reliability guarantee.
- Fewer than four checkpoints disables CV and change-point segmentation; only explicitly labeled fixed smoothing is available if the completion gate passes.
- Small sample counts, incomplete base responses, unparsed completed answers and substantial omitted branch mass generate warnings.
- The base panel shows each token's position and top-token probability. Do not assume the first few tokens contain a meaningful decision; Muse may restate the question.
- No valid dense reference means no measured reconstruction error. A dense reference is sampled independently and remains noisy; excessive cap hits withhold comparisons.

Offsets shift checkpoint positions, not text or positional embeddings. For each pass, checkpoints are `range(start + offset, end + 1, stride)`. At least two must fit. Overlapping positions across passes incur independent draws; they are not deduplicated. Add a pass with the same settings and a different seed to collect a repeat. Adding/removing/reordering passes can change the seed namespace; the recorded seeds are the source of truth.

The cost panel reports selected draws and maximum continuation-token allowances. It does not present a stride ratio as measured savings. Runtime/dollar projections require user-supplied throughput and hourly rate and exclude loading/prefix-processing overhead. Cross-branch KV reuse, adaptive sample stopping and a combined-pass estimator are not implemented.

## CLI profiles and records

```bash
.venv/bin/fork-microscope run configs/muse-smoke.json
.venv/bin/fork-microscope run configs/muse-smoke.json --prepare-only
```

Both shipped smoke profiles now use one pass. They deliberately retain small caps to test wiring and completion warnings, not to produce scientific results. Dashboard defaults use longer caps (base 512, continuation 768), which still require completion checks. `--prepare-only` loads weights and generates a base; another CLI run starts anew. Use the dashboard to sample the same in-memory base interactively.

New JSON run configuration contains `passes` plus shared `cont_max`, `temperature`, `top_k`, `threshold`, `dense`, `reference_samples`, and `tuning`. Each pass requires `id`, `label`, `start`, `end`, `stride`, `offset`, `samples`, `seed`. The independent dense reference spans the earliest through latest actual selected checkpoints. Legacy `samples/stride/shift/start/end/seed` configurations still parse as two passes, but new collection always uses per-checkpoint mixture sampling.

Every job saves `live-runs/<id>/manifest.json`, one `<pass-id>.json` per pass, optional `dense.json`, and `result.json`. Pass IDs must be unique safe names. Results/weights/credentials are excluded from Git. Completed branches are atomically saved during collection; partial-run resumption is not implemented.

Historical schema-1 results remain readable and visibly labeled legacy. Their markers used all per-branch data but fits used a subset; their older generic extractor could label truncated outputs by logit fallback. Missing decoded text and stop metadata are shown as unavailable, never invented. Original records are not rewritten.

## CPU checks and reviewer benchmark

```bash
./scripts/setup.sh cpu
.venv/bin/python -m pytest -q
node --test test_math.mjs
.venv/bin/fork-microscope run configs/cpu-smoke.json
.venv/bin/fork-microscope verify-upstream
mkdir -p outputs/review-reproduction
.venv/bin/python scripts/benchmark_review.py 40 outputs/review-reproduction/benchmark.json
```

The reviewer benchmark reproduces its reported fixed-parameter Llama replay results to four decimals. See [results and limitations](reports/README.md), including actual expected-token budgets. Separate offset fits are worse than the uniform baseline in those settings; joint fits are close. This is not a matched-token-budget or matched-accuracy savings experiment, and it does not establish a better sampling strategy generally.

The Goodfire submodule stays unmodified at `d32fed8d4162a4888291c4b3a38b059727c85a41`. Upstream tests and released-data checks exercise its original method. The strict readout, direct live mixture collection, multi-pass orchestration and viewer are our additions. Applying this workflow to Muse is a new-model experiment, not reproduction of the paper's model-specific benchmark. No GPU was used for these schema-2 changes. See [VALIDATION.md](VALIDATION.md) and [THIRD-PARTY.md](THIRD-PARTY.md).
