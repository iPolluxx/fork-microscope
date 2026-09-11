# Guided model-to-scan setup

Implemented September 10, 2026, in `public/fork-microscope/live.html`, `live.css`, and `live.js`. Existing backend endpoints, element IDs, saved data, model-loading behavior and other workers' changes are preserved. No backend or observatory files were modified by this work.

## Before and after

The previous page exposed three long forms simultaneously. Disabled actions provided little explanation, the runtime connection had no recoverable offline state, and a saved-run viewer link competed with legacy navigation.

The updated flow has three explicit stages: **Model → Question → Scan**. Only the selected stage is shown. Each step displays its readiness; users can inspect later stages before their prerequisites are available. Actions explain the missing prerequisite immediately below them and via accessible descriptions. Original-response completion advances to scan settings. The run button waits for a valid budget estimate as well as a current source response.

Primary navigation is **New scan / Explore runs**. Detailed outcome curves, continuation tables and the legacy explorer are under Advanced views. The observatory link retains the selected saved run, including after returning to New scan. Selecting a saved run records its ID in the URL for return navigation.

The runtime badge distinguishes connected, working and unreachable states. Connection failures disable actions and reveal Retry connection with guidance about runtime host, app URL and SSH forwarding. Load errors offer specific guidance for memory, model access, architecture/revision and CUDA failures. Retrying only reads status; it never launches or loads anything automatically.

Advanced sections contain model revision/device/batch, response format/length, pass names/offset/seeds, branch reconstruction, the dense reference, and optional cost projections. Core prompt, answer list, checkpoint spacing, draws and continuation length remain accessible in their relevant stage. Dark glass surfaces, consistent contrast, keyboard focus styles and narrow-screen layout match the observatory direction.

## Refinement handoff

`/live.html?source=RUN_ID#model-setup` reads `/api/live/result?id=RUN_ID`, fills the source model ID and saved resolved revision (falling back to the saved requested revision when unavailable), opens model settings, and points Explore runs back to that source. It shows that the same model must be loaded for refinement. There is no automatic model load or inference. An unavailable resolved revision still requires backend validation; the UI does not claim to prove revision identity.

`/live.html?run=RUN_ID` retains the saved-results flow. `&view=setup` opens setup while keeping that saved-run context. No new server endpoint or allowlist entry is needed.

## What this improves / what remains

**Advantages:** a visible next step, fewer simultaneous settings, clear unavailable-action explanations, preservation of the selected run, and real runtime status instead of a fabricated deployment experience. Original evidence and advanced controls remain accessible.

**Limits:** this is an interface improvement to the existing single-runtime app. It does not create RunPod pods, accept/store credentials, recommend GPUs from a live catalog, mount disks, download model-specific container images, or establish arbitrary-model compatibility. These limitations are explained in the RunPod/own-GPU disclosure. Users still need a running compatible backend. Source prefill is a convenience, not scientific identity verification. Offline saved files still need their host to be reachable to browse through this app.

## Verification

- Playwright inspected `http://127.0.0.1:8767/live.html` before and after at 1440 px desktop width; screenshots `/tmp/fork-setup-before.png` and `/tmp/fork-setup-after.png` were visually checked.
- Passed browser checks: one visible stage; model-ready/no-model action gating; prompt/scan disabled reasons; collapsed advanced defaults; add/remove pass; real saved-run source prefill with **zero POST requests**; saved run → New scan → Explore runs retaining ID; 390 px responsive model and scan states without horizontal overflow; simulated unavailable status endpoint with actionable Retry UI. No browser JavaScript errors in those checks.
- `node --check public/fork-microscope/live.js` passed.
- `.venv/bin/python -m pytest test_live.py test_sampling.py -q`: **41 passed**.
- No GPU, paid inference, cloud action, commits or pushes were performed. The disconnected state was simulated through Playwright request interception only.

## Hardware guard follow-up

The runtime's read-only `runtime.cuda_available`, `gpu_name`, and `system_memory_gb` fields now appear directly below the model ID. A known Muse-Glimmer-30B selection with Auto on a confirmed non-CUDA runtime is blocked with a GPU-worker/smaller-CPU-model explanation. Explicit CUDA is blocked when no CUDA GPU exists. Explicit CPU selection remains possible, with the large-model memory/download/speed implications visible. A compatible smaller CPU model is not blocked. Older runtimes without hardware metadata remain usable with an explicit unverified-hardware warning. These guards do not estimate VRAM or claim a detected GPU will necessarily fit the model.

Additional Playwright checks passed all six mocked hardware states with zero POST requests. Because the shared 8767 server was being restarted by its owner, these checks served the unchanged live files from an isolated temporary localhost fixture server with mocked status and an empty run list; that fixture server was closed afterward. No shared server was stopped or restarted by this work. The previous no-model idle test allowed Load because metadata was absent; confirmed CPU metadata now correctly prevents the default large Muse load. Existing source-run prefill and device/model changes recompute these guards immediately.

Final check against the restarted real server at `http://127.0.0.1:8767/live.html`: actual status displayed **CPU runtime · 15.5 GB system memory · No CUDA GPU detected**. The default Muse-Glimmer-30B/Auto Load button was disabled with the GPU-worker/smaller-model explanation. Zero POST requests. Screenshot: `/tmp/fork-setup-hardware-final.png`.
