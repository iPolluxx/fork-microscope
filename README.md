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

New custom-prompt runs match 1–32 expected answer texts anywhere in a completed reply. The answer list is tracking metadata and is not appended to the prompt. Matching normalizes Unicode (NFKC), case and repeated whitespace, with word boundaries on word-like ends. It does not recognize semantic equivalents or negation. One distinct match gets that label; multiple distinct matches, no match or a capped output become Other. `Other` is reserved; answer strings must be unique after normalization. An answer such as `56` will not match `156`, but “I reject 56” will match. Inspect the saved matched answers and text before interpreting the curves.

For generic models, an explicit `<think>…</think>` prefix is excluded; untagged reasoning remains part of the searchable response. No universal reasoning-channel parser is claimed. Legacy question/choices configurations keep the original A–D regex. Neither path forces a logit fallback. Muse only reads a completed `to=user` channel; both `<|eot|>` and `<|end_of_text|>` stop generation, while `<|eom|>` only ends a channel. Upstream strips the terminal EOS, so stop reason is inferred from the forced token or stripped length and the exact removed EOS identity is not fabricated.

## Dashboard workflow

1. **Setup & sample:** attach a compatible HF model ID or server-local model directory, write your exact prompt, and enter expected answers (one per line). Generate the base trace, then choose checkpoint region, spacing, draws and continuation cap. Add passes only when needed.
2. **Results:** select a saved run, choose an outcome, and inspect its observed frequencies and eligible fitted curves. Clicking an observed point opens its evidence.
3. **Continuations:** navigate pass → all checkpoints or one checkpoint → draw. Filter by outcome, completion or ambiguity and search the saved text. The paginated list opens a reader with new continuation text, full response, matcher input and token IDs. Old runs remain browsable with missing fields labeled unavailable.

**Length versus count:** at checkpoint 60, retain original tokens 0–59, choose one branch token at 60, and generate up to `cont_max` new tokens after it. EOS can stop earlier. Each draw starts from the same checkpoint prefix, not the preceding draw. Spacing 4 visits every fourth position; 20 draws collects 20 continuations at each visited position. The cap limits each continuation’s length, not the checkpoint spacing or number of draws.

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

The original CPU and Muse smoke profiles use one pass and deliberately retain small caps to test wiring and completion warnings, not to produce scientific results. `cpu-custom.json` exercises free-form prompts and numeric text matching with a 64-token continuation cap; it is also a small pipeline check. Dashboard defaults use longer caps (base 512, continuation 768), which still require completion checks. `--prepare-only` loads weights and generates a base; another CLI run starts anew. Use the dashboard to sample the same in-memory base interactively.

A custom `base` object uses `prompt` (up to 16,000 characters), `answers` (1–32 strings, each up to 200 characters), `mode` (`chat` or `base`), `max_tokens`, and `seed`. See `configs/cpu-custom.json` for a runnable example. The legacy `question` plus four `choices` object remains supported.

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


## Muse anticipation question

`configs/muse-anticipation.json` preserves the exact question: “In your reasoning do you anticipate future turns in the conversation when you give your final output?” It tracks the literal texts `yes`, `no`, and `uncertain`; absent or multiple matches become Other. These labels are not appended to the prompt. A reply such as “I do not anticipate later turns” may therefore be Other. Review the recorded replies before interpreting this self-report measurement.

Generate and inspect the base first. In the dashboard, use this prompt and answer list with a 2,048-token base cap. Then choose early/middle/later checkpoints on the actual trace, five draws each, and a 2,048-new-token continuation cap. The profile's positions 0, 64 and 128 are provisional: adjust after reading the trace, and do not run them if the response is shorter than 129 tokens. Three checkpoints are a completion/readout pilot, not enough for change-point segmentation. Nothing in the Docker startup automatically runs this experiment.

Variation in the model's answer to this question is evidence about its generated self-report. It does not establish that the model internally plans for future conversation turns. The continuation sampling here contains no later user turns.
