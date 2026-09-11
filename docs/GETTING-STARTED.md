# Your first Fork Microscope session

The [hosted dashboard](https://fork-microscope-wzyjs4vwsq-uc.a.run.app) displays controls and evidence. A **worker** is the application running on your computer or GPU VM. It reads your model and stores results there. Each user owns their worker; there is no shared GPU account or hosted inference included.

## 1. Install the worker

The tested setup is Linux x86-64, Git, and [uv](https://docs.astral.sh/uv/getting-started/installation/). A checkout is required; a source ZIP does not include the upstream submodule. macOS/Windows installation is not yet a tested release path.

```bash
git clone --recurse-submodules https://github.com/iPolluxx/fork-microscope.git
cd fork-microscope
./scripts/setup.sh cpu
```

For an NVIDIA GPU worker with a CUDA 12.8-compatible driver, use `./scripts/setup.sh cuda` instead. CPU setup can inspect saved evidence and run models small enough for the machine. Muse-Glimmer-30B previously ran on an A100 80GB; do not try loading that model on an ordinary laptop just to test the interface.

The script creates `.venv`, installs pinned dependencies and checks the environment. It downloads no model weights. The pinned Goodfire source is obtained from its public repository; its terms are separate from this project's MIT license. See [third-party provenance](../THIRD-PARTY.md).

## 2. Start and connect

From the installed project folder:

```bash
.venv/bin/fork-microscope connect \
  --dashboard-origin https://fork-microscope-wzyjs4vwsq-uc.a.run.app
```

The command prints:

```text
Worker URL: http://127.0.0.1:8767
Worker access token: <a random value generated on your computer>
```

Open the dashboard, select **Connect worker**, paste the URL/token and select **Test and connect**. The token is a password for this worker, not a cloud provider key. It is generated on startup unless you explicitly set `FORK_WORKER_TOKEN`; restarting the command without an existing token generates a new one. Keep the terminal running. Ctrl+C stops the worker.

`127.0.0.1` means the computer where your browser runs. To use a VM, run the worker command on the VM and forward the same port from your browser's computer:

```bash
ssh -N -L 8767:127.0.0.1:8767 USER@VM_HOST
```

Keep both processes running. The browser URL stays `http://127.0.0.1:8767` and the token is the value generated on the VM. Provider-specific SSH usernames/ports must match your VM. A custom/public worker endpoint needs HTTPS; [the hosting guide](HOSTED-DASHBOARD.md) covers that route.

If your browser blocks the website's localhost connection, open `http://127.0.0.1:8767` to use the worker's own dashboard and connect with the same token. No public port exposure is required for local use or SSH tunneling.

## 3. Attach a model

In **Configure**, choose a Hugging Face model ID or a local model directory, inspect it, then load. A folder path is on the **worker**, not necessarily the computer showing the website. For example, `/home/alex/models/my-model` must contain native Hugging Face configuration/tokenizer/safetensors files on that worker. The model is not uploaded to the hosted dashboard.

Native Transformers text models and specialized Muse handling are implemented. Metadata inspection is an eligibility check, not proof that every model works. GGUF/Ollama, ordinary chat API endpoints, custom remote code and pre-quantized checkpoints are not supported adapters. Private/gated model login happens on the worker.

## 4. Run a small, inspectable scan

Enter a prompt and answer labels that can actually appear in a completed reply. For a first task, request an explicit short final marker such as `DECISION=LAUNCH` or `DECISION=DELAY`. The current matcher detects text mentions; mentioning both labels can become `Other`. This is not a semantic judge.

Generate the original response first. Inspect whether it completed, then choose a small checkpoint range, 5–20 draws per checkpoint and a continuation cap suited to the response. These are starting settings, not a reliability or runtime guarantee. Review the budget before generating continuations.

- **Checkpoint spacing:** how far apart positions are on the original response.
- **Draws per checkpoint:** how many new continuations are generated from each sampled prefix.
- **Continuation cap:** the maximum new tokens per continuation. It is not the number of checkpoints.

## 5. Read, refine, compare and save

In **Explore**, inspect raw frequencies, saved fitted estimates, uncertainty and the actual continuation text. A change interval is a candidate for investigation, not a significance test. A flat curve is also a valid result.

Select an interval to sample more closely. The saved original token sequence is reused exactly; a new original response is not substituted. The reference preset can be expensive: every token with 100 draws. Inspect its budget before starting.

In **Compare**, select compatible original/refinement passes. Only compatible evidence receives metrics. A larger finite sample is a reference, not ground truth. Export evidence and prompt sets before terminating an ephemeral VM.

## Need help?

[Open an issue](https://github.com/iPolluxx/fork-microscope/issues/new/choose) with your OS, model ID/revision, hardware, the step that failed and sanitized errors. Do not include access tokens, private model credentials or private prompt/result data.
