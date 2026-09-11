# Native model attachment implementation

September 10, 2026. Owner: Mirage. All changes are local. No model weights, GPU jobs, container build, registry update or deployment were started.

## Delivered

- A generic Model step with an empty initial model field, Hugging Face/local-worker-directory picker, metadata inspection, blockers, context/format information and explicit Load action.
- Hub inspection resolves a mutable revision to its immutable commit and displays/preserves that commit for loading. Changing the model ID invalidates inspection and clears an inherited commit.
- The metadata-only `preflight_model(payload, runtime)` inspects native configuration/tokenizer metadata. It never calls a model weight loader. Where Hub safetensors metadata exposes parameter totals, it estimates full-weight memory at the adapter's load dtype. It labels excluded KV cache, context, batch and allocator costs. Local stored-weight size is not falsely presented as resident memory.
- Native Transformers causal checkpoints and the specialized Muse text adapter are eligible. Unsupported architecture mappings, pre-quantized configurations, missing context limit, missing tokenizer requirements, unavailable requested CUDA and clearly insufficient weight memory produce actionable blockers.
- Local directories receive a `local-sha256:<digest>` resolved revision based on actual safetensors/config/tokenizer contents. The loader rejects a supplied saved fingerprint if files differ, canonicalizes the directory path and checks for changes while loading.
- Docker now starts without a selected model and with autoload disabled. Explicit `AUTO_LOAD_MODEL=1` plus `FORK_MODEL_ID` or `FORK_MODEL_PROFILE` enables intentional startup attachment. Generic explicit IDs use `main` unless a revision is supplied; changing a profile model must explicitly replace the profile's revision.
- Docker autoload includes `FORK_WORKER_TOKEN` in the Authorization header when configured, without printing or putting the token in a URL.
- Model controls use the commander's shared worker transport. Worker switches clear inspection and visible run/model state. Evidence download uses an authenticated fetch and a local download blob.
- Navigation links Workspace, Configure, Explore and Compare. `?set=<id>&prompt=<id>` restores a saved prompt's text, answers, format, cap and seed without generating anything.

## Integration contract

`POST /api/live/model-preflight` uses the same four load fields: `model_id`, `revision`, `device`, `batch_size`. The callable is `model_preflight.preflight_model(payload, runtime)`.

Its result includes `model_id`, `requested_revision`, `source_type`, `resolved_revision`, `device`, `architecture`, `loader`, `chat_template`, `context_limit`, `parameters`, `blockers`, `warnings`, `can_load`, `verification: metadata_only`, `capabilities` and `memory`.

`runtime` may expose `cuda_available`, `gpu_name`, `gpu_memory_gb`, `gpu_free_gb`, `system_memory_gb` and `system_available_memory_gb`. If free memory is absent, total memory is only a hardware ceiling; it does not prove available capacity.

`AttachedModel.info` now carries `source_type` and `identity_kind` plus capabilities. `resolved_revision` is either an immutable Hub commit or a local content fingerprint. `same_model_identity(left, right)` permits local snapshots with the same complete content fingerprint to move to different worker directories. Hub assets still require the same repository and resolved revision. Replay uses this helper, and the coordinator applies the same rule to refinement eligibility; comparison adds its own pinned-revision evidence validation. Missing or malformed local fingerprints never qualify by matching paths alone.

A preflight `can_load` result is eligibility, not successful generation or semantic answer-parser validation. The button makes weight loading explicit. Worker APIs and CLI automation can still intentionally request attachment directly; they must report real loader failures.

## Validation

- 29 model/preflight tests passed. These cover no weight calls during metadata inspection, immutable Hub refs, local hashing and changed contents, missing access without secret echo, unsupported formats/quantization, missing CUDA, memory blockers, no chat template, opt-in Docker defaults and Authorization headers.
- Two existing exact-replay tests passed with the new adapter imports.
- Seven packaging tests passed. No image was built.
- Browser QA passed nine flows with mocked worker metadata: empty initial state, inspect-before-load, revision pinning, stale-inspection invalidation, local source selection, explicit load, saved-prompt restoration, worker switching and mobile overflow checks. No JavaScript errors; exactly one intentional mocked load. No actual model download occurred.
- Desktop/mobile screenshots were visually inspected. `live.js` syntax and `git diff --check` passed.

## Remaining limits

The adapter uses full weights on one CPU/CUDA device. It does not add GGUF/Ollama, generic chat APIs, quantization, multi-GPU sharding, MPS or provider provisioning. Native eligibility can cover many architectures but only real tested model runs establish support quality. Small smoke runs should verify EOS behavior, prompt templates and answer parsing for each intended model family.

Local content hashing intentionally reads weight files at attachment and can add startup time for large models. It provides stronger identity than path/mtime alone. Memory inspection cannot predict continuation-cache growth accurately, so users still need capacity headroom and should validate their selected batch/context with a short run.
