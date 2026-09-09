# Fork microscope

A local dashboard and CLI for sampling an open-weight model at two offset sets of checkpoints on the **same fixed response**, then reconstructing and comparing its outcome curves with Goodfire's Forking Fast code.

This repository packages a research workbench, not a new validated research method. It keeps the original and shifted readouts separate. It does not yet implement automatic selection of a statistically sufficient sample count or an estimator that combines the two curves.

## RunPod Docker template

For a prebuilt environment with automatic dashboard startup and Muse loading, see [the container instructions](docker/README.md). The image build workflow is manually triggered; it does not allocate a GPU.

## Start on a GPU VM

Use a Linux x86-64 NVIDIA GPU VM. The initial Muse profile uses full BF16 weights, one concurrent continuation, and short token caps. An 80 GB GPU is the starting hardware target; this is a capacity estimate, not a completed GPU benchmark. Allow roughly 150 GB of persistent disk for weights, the environment, and results. Longer contexts and larger concurrent batches require more memory. An NVIDIA driver compatible with CUDA 12.8 is required; the setup installs the Python CUDA runtime dependencies.

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/) if the VM image does not include them. Authenticate to GitHub on the VM using your own account or a repository-scoped credential because this repository is private. No credentials are included here.

```bash
git clone --recurse-submodules https://github.com/iPolluxx/fork-microscope.git
cd fork-microscope
./scripts/setup.sh cuda
.venv/bin/fork-microscope doctor --muse
```

`setup.sh` provisions Python 3.13 through uv, installs a pinned CPU or CUDA dependency set, installs both upstream packages at the pinned submodule revision, and registers the CLI. `doctor --muse` checks the exact Muse configuration, tokenizer, chat template and empty-weight architecture without downloading its model weights. Confirm that `cuda_available` is `true` on the VM.

The supported installation is this Git checkout plus its editable Python package. Keep the checkout and its `public/`, `configs/`, and `vendor/` directories together. A standalone wheel is not the distribution format.

## First Muse run

The versioned profile is [configs/muse-smoke.json](configs/muse-smoke.json). It pins `meta-models/Muse-Glimmer-30B` to revision `a4e59da52a7bc87ae7251dd5545c0dd437c44b68`.

```bash
.venv/bin/fork-microscope run configs/muse-smoke.json
```

This downloads and attaches the model, generates a greedy base response, collects five continuations per retained branch at checkpoints `[0,16]` and `[1,17]`, and fits Goodfire's M5a segment-kernel reconstruction with cross-validation. The continuation cap is 128 tokens. These tiny settings check the wiring; they cannot establish reliability, savings at matched accuracy, or a substantive finding. Muse may use the entire allowance for reasoning, resulting in `Other` rather than a completed answer.

For a base response and sampling-budget estimate without collecting branches:

```bash
.venv/bin/fork-microscope run configs/muse-smoke.json --prepare-only
```

This still loads the weights and generates the base response. A subsequent `run` starts a new job and regenerates the base; the CLI does not resume that prepared session. Use the dashboard to inspect and sample the same in-memory base interactively.

If the generated response is shorter than the configured endpoint, choose an earlier valid endpoint or a different question. The program rejects out-of-range grids rather than silently changing the experiment. Increase token caps and check completion rates before interpreting a larger experiment. `batch_size` controls concurrent execution; `samples` controls continuations per retained branch. They are different settings.

## Dashboard and local model directories

On the VM:

```bash
.venv/bin/fork-microscope serve --port 8767
```

On your own computer, add the following port forwarding to your VM's SSH command, replacing `USER@VM_HOST` with the provider's actual login:

```bash
ssh -N -L 8767:127.0.0.1:8767 USER@VM_HOST
```

Open **http://127.0.0.1:8767/live.html**. Port 8767 avoids the existing playground on 8766. The server listens on VM loopback and validates request origins; use SSH forwarding rather than exposing its model-control API publicly. Keep the browser's local port and the server port identical because the server validates the HTTP Host header. For a different port, change all three occurrences consistently.

The dashboard can attach a Hugging Face model ID or an absolute model directory **on the machine running the server**. A local directory needs the complete Transformers configuration, tokenizer/processor, and safetensors weights. It is not a GGUF loader or a connection to Ollama. Muse uses `AutoModelForImageTextToText`; other models use `AutoModelForCausalLM`. Custom remote Python code is disabled. Support is conditional on the model architecture being supported by the pinned Transformers release, fitting memory, and the A–D answer readout being compatible. This is not a promise that every open-weight model will work.

Your own GPU workstation uses the same setup and can open localhost directly. Colab would need this environment running inside its runtime and a compatible connection method; this package does not establish a Colab connection automatically.

## What comes from Goodfire

The `vendor/forking-fast` Git submodule points to [ericb-goodfire/forking-fast](https://github.com/ericb-goodfire/forking-fast) at `d32fed8d4162a4888291c4b3a38b059727c85a41`.

The live path uses upstream exact-token branch enumeration, standard batched resampling, probability-weighted outcome vectors, mixture draws, five-fold cross-validation, M5a segmentation/smoothing, and nominal 90% bands. Optional dense sampling collects separate continuations and supports total-variation, held-out log-likelihood, and band-coverage comparisons. All five answer categories are retained; category selection does not use the reference.

The native model loader, dashboard, two-grid orchestration, durable records, and Muse answer extraction are this project's additions. Muse is stopped at `<|eot|>`, not the intermediate channel-ending `<|eom|>`. Only a completed `to=user` channel supplies its A–D answer; unfinished or unparseable turns are `Other`. Other supported models use upstream regex extraction followed by the A–D logit fallback. This model-specific extraction difference matters when comparing results across models.

Checkpoint offsets are measured in response token IDs, including Muse's channel headers and special tokens. They shift **where the same trace is sampled**; they do not insert text or shift positional embeddings. Candidate change boundaries and outcome shifts are behavioral measurements, not proof of an internal causal mechanism.

The cost panel counts actual retained branches and maximum continuation allowances. Dollar/time projections need your measured throughput and GPU rate, and exclude loading and other listed overheads. A lower sampling allowance does not establish equal information or measured cost savings. The two-grid run can be compared with an independent dense reference, but its finite-sample reference is itself noisy. Cross-branch KV-cache reuse and adaptive sample stopping are not enabled.

## Verify Goodfire's released data and mathematics

These checks use CPU and released data; no model weights are needed:

```bash
.venv/bin/fork-microscope verify-upstream
mkdir -p outputs
OTRECON_FORCE_RUPTURES=1 .venv/bin/python vendor/forking-fast/otrecon/src/run_scale.py gate \
  --data-dir vendor/forking-fast/data/s200 --out outputs/upstream-gate
```

`verify-upstream` checks all released data hashes, the reference curve round-trip, and the upstream Python test suites. `gate` runs Goodfire's recorded numerical validation targets. The full replicate-fan benchmark is available through upstream `otrecon/src/run_scale.py` (`fan` and `assemble`); see its docstring and `--help` before selecting a larger CPU workload. These checks do not claim to rerun the entire paper.

The paper's released stores contain Llama/DeepSeek outcomes. Reading them does not load those models. Applying the method to Muse is a **new model experiment**, not a reproduction of the published model results. This package uses the upstream library components directly rather than its generic sampling CLI, whose pinned version has an undefined `report_progress` call in its reporting path.

## Results and recovery

Every collection writes `live-runs/<run-id>/`: model revision and environment metadata in `manifest.json`; exact prompt/base token IDs, branch token IDs, probabilities, continuation IDs and labels in `first.json` and `second.json`; optional `dense.json`; and the fitted curves/metrics in `result.json`. The dashboard can reopen completed runs and export the records as JSON.

Put the checkout's `live-runs/` directory and your Hugging Face cache on persistent VM storage. Copy results off the VM before deleting it. Results, environments, weights and credentials are excluded from Git. Partial completed branches are saved on cancellation/error, but automatic resumption of partial runs is not implemented. Stop requests take effect at sampling boundaries, not in the middle of a model generation call.

## CPU development check

```bash
./scripts/setup.sh cpu
.venv/bin/python -m pytest -q
node --test test_math.mjs
.venv/bin/fork-microscope run configs/cpu-smoke.json
```

Node is only required for the frontend math tests, not to serve the application. The CPU smoke profile downloads a small SmolLM2 model and runs both grids, an independent dense reference, and cross-validated reconstruction. It is a software test, not the research target.

See [VALIDATION.md](VALIDATION.md) for tested scope and [THIRD-PARTY.md](THIRD-PARTY.md) for provenance and license boundaries.
