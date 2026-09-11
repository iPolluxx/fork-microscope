# Fork Microscope

**Inspect where model outcomes change. Sample more closely. Read the evidence.**

[Open dashboard](https://fork-microscope-wzyjs4vwsq-uc.a.run.app) · [Get started](docs/GETTING-STARTED.md) · [Engineering case study](docs/PORTFOLIO.md) · [Report an issue](https://github.com/iPolluxx/fork-microscope/issues)

[![CPU and dashboard checks](https://github.com/iPolluxx/fork-microscope/actions/workflows/checks.yml/badge.svg)](https://github.com/iPolluxx/fork-microscope/actions/workflows/checks.yml)

A workbench for exploring where a model's possible answers change along a generated response. Attach your model, sample continuations at checkpoints, inspect the actual text, then collect more evidence around an interesting interval.

Built around [Goodfire's Forking Fast](https://github.com/ericb-goodfire/forking-fast). The contribution here is the research workflow: custom prompts, configurable passes, exact-trace refinement, portable evidence, and a connected interface. These are behavioral measurements, not proof of an internal reasoning mechanism.

![The observatory: outcome map, recorded draws and checkpoint inspector](docs/images/observatory.jpg)

**Status: v0.1.0-beta.1 — research beta.** The public website is the interface; generation requires your own worker and suitable hardware. Fork Microscope's own code is MIT licensed. The pinned Goodfire dependency has no license file; permission for public redistribution of a bundled worker/image remains unresolved. See [third-party provenance](THIRD-PARTY.md). No model weights or personal runs are included.

## What you can do

- Connect your own local machine or GPU VM to the dashboard.
- Inspect and attach native Hugging Face checkpoints or local safetensors model directories.
- Save multiple prompt sets and run selected prompts sequentially on one model.
- Configure up to eight passes, each with its own region, spacing, offset, draw count and seed.
- View raw outcome frequencies alongside the Goodfire reconstruction, then read every recorded continuation.
- Restore the exact original token sequence for a denser refinement or reference run.
- Compare compatible saved runs and export evidence or prompt sets before replacing disposable hardware.

The workflow is **Workspace → Configure → Explore → Compare**. Starting the app downloads no model. Model attachment and sampling are explicit actions.

## Install from a checkout

Tested on Linux x86-64. You need Git and [uv](https://docs.astral.sh/uv/getting-started/installation/). The setup script installs Python 3.13 and the pinned dependencies into `.venv`. Node.js 22 is needed for the JavaScript test suite, not normal use.

```bash
git clone --recurse-submodules https://github.com/iPolluxx/fork-microscope.git
cd fork-microscope
./scripts/setup.sh cpu
.venv/bin/fork-microscope serve --port 8767
```

Open **http://127.0.0.1:8767/**. CPU setup is suitable for viewing saved evidence, the upstream recorded-data explorer, and small model checks. No model weights download during setup. Use `./scripts/setup.sh cuda` instead on an NVIDIA worker with a CUDA 12.8-compatible driver. This is a checkout-based application; `pip install .` alone does not install its complete environment or create a standalone distribution.

For a remote worker, forward its port over SSH:

```bash
ssh -N -L 8767:127.0.0.1:8767 USER@VM_HOST
```

See [container setup](docker/README.md) for the Docker path. This repository publishes Fork Microscope’s own source and an upstream Git reference. It does not bundle the upstream checkout or datasets in release archives. A public prebuilt GPU worker image is not offered while upstream redistribution permissions remain unresolved.

To connect the hosted website to this installation, run:

```bash
.venv/bin/fork-microscope connect \
  --dashboard-origin https://fork-microscope-wzyjs4vwsq-uc.a.run.app
```

This starts the local worker and prints its URL and a generated access token. Paste both into **Connect worker** on the website. Keep the terminal running. No model is downloaded or loaded by this command. See [the walkthrough](docs/GETTING-STARTED.md) for local model folders, GPU setup and SSH tunnels.

## Run your first investigation

1. **Configure:** enter a model ID or worker-local directory. Inspect compatibility, then load. Gated/private model access is configured on the worker through Hugging Face authentication.
2. **Question:** enter your exact prompt and the answer texts to track. Generate and inspect the original response.
3. **Scan:** choose checkpoint positions, draws per point and a new-token cap. Review the budget and start sampling.
4. **Explore:** select an outcome, inspect its raw points and fitted curve, and read the recorded draws. A fitted boundary identifies a candidate interval for investigation.
5. **Refine:** select that interval or the whole original trace. Adjust density and draw count; the reference preset is every token with 100 draws. Review its budget before starting.
6. **Compare:** select the original and new saved passes. The app checks identity and sampling compatibility before showing metrics. Export the evidence when finished.

For many questions, create a prompt set in **Workspace** and select which prompts to run. The worker executes them sequentially; each prompt gets its own trace and result. Editing a set does not change an already started batch.

## How to read the graph

A checkpoint's raw point measures how often each answer label appeared among newly generated continuations from that exact prefix. **S means total draws per checkpoint, not per candidate token.** Candidate branches are selected using renormalized probabilities over the retained tokens. The app records omitted probability mass.

The smoothed curve uses Goodfire's segment-kernel estimator with cross-validation or explicit fixed parameters. A curve is an estimate, and a highlighted change interval is not a significance test. Answer tracking detects text mentions; it does not determine semantic correctness. Multiple matches, missing matches and unfinished replies count as `Other`.

A larger reference is still a finite sample. The comparison view distinguishes raw shared-checkpoint differences from fit-versus-new-checkpoint measurements. Different traces, incompatible settings and duplicated observations cannot produce a valid comparison score.

See the [method and experiment reference](docs/REFERENCE.md), [numerical audit](reports/consumer-readiness/math-audit.md), and [validation record](VALIDATION.md).

## Host the dashboard; let users bring compute

```bash
python3 scripts/build_dashboard.py
```

Publish the generated `dist/dashboard/` folder, or unpack `dist/fork-dashboard.zip`, on an HTTPS static host. It includes license notices and excludes upstream Python code/data, models, run records and credentials. Each visitor connects an independently owned worker using a worker URL and access token. A worker can serve its own copy of the dashboard too.

[Hosted dashboard instructions](docs/HOSTED-DASHBOARD.md) cover allowed origins, authentication, browser local-network restrictions, SSH/HTTPS and backups. There are no central accounts, shared GPU service, or cloud-provider credentials in this design. A worker is for one user or trusted team; unrelated visitors need separate workers.

## Supported scope and limits

| Area | Current scope |
| --- | --- |
| Model adapter | Native Transformers causal models plus specialized Muse handling; eligibility is inspected, not universal model certification. |
| Formats | Hub/native safetensors directories. GGUF/Ollama, arbitrary chat APIs, custom remote code and pre-quantized checkpoints need other adapters. |
| GPU validation | Prior Muse-Glimmer-30B runs used an A100 80GB. Broader model/hardware acceptance is still needed for this release. |
| Reproducibility | Pinned Hub revisions or local content fingerprints, saved exact token IDs, settings, draws and lineage. Hardware/library changes can affect numerical behavior. |
| Recovery | Completed results and partial records survive cancellation. Automatic partial-draw resumption is not implemented. |
| Editing | Token-edit drafts can be exported; edited-text generation and activation interventions are not connected. |
| Cost | Draw/token budgets and conditional timing projections. No guaranteed runtime or matched-accuracy savings. |

## Feedback that helps

Try a small scan on a supported model and report where setup or interpretation becomes unclear. Useful first contributions include model compatibility reports, clearer answer extraction, and improvements to reading/comparing recorded continuations. Include the model revision and hardware; never include your worker token.

## Contribute and verify

```bash
.venv/bin/python -m pytest -q
node --test test_*.mjs
.venv/bin/fork-microscope verify-upstream
python3 scripts/build_dashboard.py
```

These checks use CPU or saved data; they do not start a GPU VM. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the layout, contribution scope and test expectations, and [SECURITY.md](SECURITY.md) for the worker's trust boundary and safe reporting. The [release review](reports/public-release/README.md) records what was checked and what remains unresolved.

## License and attribution

[MIT](LICENSE) covers this project's own code. Third-party components retain their own terms; the MIT grant does not relicense the upstream Git submodule, its datasets or model weights. Plotly's MIT notice is retained in [licenses/plotly-MIT.txt](licenses/plotly-MIT.txt). Goodfire attribution and recorded upstream revisions remain visible in the interface. This project is independent and does not imply Goodfire endorsement.
