# Model loading implementation — 2026-09-09

Implemented configurable startup and a transfer tuning option, while preserving the pinned
Muse default, full precision loading behavior, model-native sampling, and ephemeral disks.
No GPU resource was started and no image was published by this work.

## Delivered

- Docker build arguments can select a profile or explicit model/revision without reinstalling
  dependencies. The same selection is overridable at deployment time; no rebuild is required.
- Startup rejects a changed model ID with an inherited Muse revision. Four-field load profiles
  and existing complete experiment profiles both work. Legacy AUTO_LOAD_MUSE remains compatible.
- Startup saves selection, reports actual async job completion/failure, and logs readiness.
  Disabling auto-load makes no HTTP load request; invalid configuration leaves the UI and SSH up.
- HF Xet high-performance transfer is enabled in the container and can be disabled. Existing
  pinned hf-xet and hub versions support it. It may use more CPU/bandwidth; speedup unmeasured.
- Reuse AutoConfig in model construction; tokenizer and weights use its resolved Hub commit,
  preventing a mutable branch from resolving to different snapshots during one attachment.
- Config/tokenizer/weights/total durations and transfer settings are saved in model metadata.
  Weight duration combines download with loading, rather than claiming separate measurements.

## Important findings

Our pinned Transformers 5.16.1 already uses asynchronous tensor loading by default with up to
four threads. Its source `core_model_loading.py` uses HF_DEACTIVATE_ASYNC_LOAD; older parallel
loading flags mentioned in Transformers documentation have no effect in this installed version.
We did not add ineffective flags or count existing async behavior as a new speedup.

The existing A100 test validates the old container end to end, including 15 completed draws.
The parent-provided operational timing was ~134 seconds total including ~60GB download and
~10 seconds GPU loading; the checked-in session report records run success but does not contain
those loading timings, so they are contextual observations, not a reproducible new benchmark.
Download cost is therefore the suspected main cold-load bottleneck. New timings will let the
next run record comparable stages; network and model-to-GPU time are not separated yet.

Baking ~60GB weights into an image shifts bytes to registry pull and extraction; it cannot be
assumed faster on a fresh host. Default image continues to download weights once per ephemeral
cache. Same-Pod reload reuses cache; a deleted Pod does not preserve it.

## Validation and integration

Dedicated tests: `test_model_loading.py`. Existing compatibility tests: `test_packaging.py`.
These cover profile/env precedence, unsafe inherited revisions, invalid selections, disabled
startup, accepted-vs-completed jobs, failure reporting, config reuse, immutable commit propagation
for both Muse and generic adapters, unchanged dtype/safetensors/device arguments, and timings.
Parent owns adding this test file to default testpaths, wiring the optional progress callback
in LiveService, and performing the final integrated local image build and startup check.

Primary documentation consulted:
- https://huggingface.co/docs/huggingface_hub/en/package_reference/environment_variables#hfxethighperformance
- https://huggingface.co/docs/transformers/en/reference/environment_variables

The installed code takes precedence over the latter page's stale parallel-loading settings.
RunPod's installed image/build and bake-vs-mount playbooks informed the disk tradeoff.

Local validation result: **21 passed** across `test_model_loading.py` and `test_packaging.py`
(6.46 seconds). `git diff --check`, `bash -n docker/start.sh`, and offline
`python docker/autoload.py --print-config` passed. The resolved default remains Muse revision
`a4e59da52a7bc87ae7251dd5545c0dd437c44b68`, CUDA, batch size 1.
