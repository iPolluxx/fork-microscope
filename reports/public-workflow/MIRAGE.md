# Mirage architecture review: a reproducible public workflow

Date: September 10, 2026. Scope: code-informed architecture and acceptance criteria for the current implementation turn. This review does not certify broad model support or central multi-user hosting.

## Architecture update after user clarification

The commander subsequently confirmed a **public static dashboard plus each user’s own worker**. The public UI does not host models or store all users’ evidence centrally. An authenticated worker opts into allowed dashboard origins; the shared connection transport supplies the worker token. The implementation below therefore supports separate dashboard/worker origins as well as an all-in-one local installation. The original self-hosted-only recommendation below records the initial review, not the final hosting contract.

## Initial decision

Ship one coherent, self-hosted workbench with three connected destinations: **Workspace → Configure and run → Explore and compare**. Each installation owns its models, prompt sets, jobs and evidence. A browser user should not need an agent to move JSON files, restore a trace, select saved runs or launch a set of prompts.

Retain the current Goodfire estimator unchanged. Expand orchestration around it, not its scientific claims. A larger reference is a finite independent measurement; disagreement with it is not automatically true estimation error, and a highlighted PELT interval is not a significance test.

Central SaaS with shared credentials and many simultaneous unrelated users is a different deployment contract. The present `ThreadingHTTPServer`, one global `LIVE` object, filesystem paths and no authentication cannot truthfully be described as that service. The useful public release is an installable open-source application, with a separate instance for each user or trusted team.

## What the checkout supports today

- `live_model.py` already loads arbitrary native Transformers `AutoModelForCausalLM` repositories/directories plus the specialized Muse loader. It pins Hub configuration, tokenizer and weights to the resolved commit, prohibits remote custom code, and uses safetensors.
- Model support is constrained by the installed Transformers version, standard causal generation, accessible tokenizer, EOS/pad behavior, available memory, and text-channel parsing. The current UI's pinned Muse default is a personalization problem, not proof that the core adapter only supports Muse.
- `LiveService` has one attached model and one cancellable job. `base`, `run`, `refine` and unload work through real API calls. A dense reference can already be collected in the same run and compared by TVD, held-out log likelihood and band coverage.
- Completed evidence is durably written and portable; refinement restores saved token IDs and retains parent lineage. The continuation library and observatory inspect real text and counts.
- There is no saved prompt-set workspace, batch orchestration, arbitrary saved-run comparison, generic preflight, or automatic provider deployment in the app. The prior agent-operated VM workflow must not appear as a working product button.
- The default Docker autoload currently selects Muse. `test_model_loading.py` explicitly tests that default. Standardizing the default requires intentionally updating that behavior and those tests, not merely changing the HTML field.

## Model attachment contract

The primary choices should be **Hugging Face repository** and **Local model directory on this worker**. They feed the same native adapter and preserve the exact-token workflow. An optional **Remote GPU worker** choice should clearly mean opening an already running Fork Microscope worker through a localhost tunnel, not passing an ordinary chat-completions endpoint as a model.

Do not advertise Ollama, GGUF, generic OpenAI-compatible APIs, vLLM chat endpoints or arbitrary hosted inference as FPA-compatible. This application requires all of:

1. Exact tokenizer IDs and faithful decode, including special tokens.
2. Next-token log probabilities at every recorded base position.
3. Forcing a selected candidate token and continuing from an exact prefix.
4. Deterministic identification of model/tokenizer revision and sampling configuration.
5. Enough context and a recognizable end of response.

Any future adapter can implement these capabilities, but a chat API alone does not establish them. Describe untested native architectures as **eligible for attachment**, not verified compatible models.

### Preflight and load

Recommended POST `/api/live/model-preflight` request: `{model_id, revision, device, batch_size}`. It may fetch configuration/tokenizer metadata but never model weights. Return a stable object containing model/source type, resolved revision, architecture and supported loader, chat-template support, context limit, memory estimate with its assumptions, observed hardware, warnings, blockers and `can_load`.

The Load button remains an explicit mutation at `/api/live/load`. A preflight is advisory because metadata does not guarantee weight availability or memory fit. Its result must be invalidated when any corresponding field changes. Show the worker's hardware and path semantics next to the form. Never silently download a 30B model on first visit or container start. Start with an empty model selector; examples/presets should fill fields without triggering a download.

Hub refs resolve to a commit. Local directories need a local model identity/fingerprint, because `_commit_hash` can be absent. Source IDs and a friendly path alone cannot ensure that local weights remain unchanged for refinement or comparison. A local fingerprint should cover the model/config/tokenizer files that determine behavior, or the app must clearly withhold exact-revision claims for unverified local assets. Do not let a local-directory load appear fully supported while saved-trace refinement fails later due to a missing Hub revision.

Gated/private Hub access belongs in worker-side Hugging Face login/environment for this release. Do not store API keys in prompt-set JSON, URLs, exports or browser localStorage. One-click RunPod creation would need a distinct authenticated provider integration, lifecycle and backup model; do not add a decorative deployment button.

## Prompt sets and queue

Provide a workspace of named sets, each containing stable-ID prompts with prompt text, answer texts, prompt format, base cap and base seed. Selecting a saved prompt fills the existing Question step without generation. Editing and saving creates an intentional new revision/snapshot; a queued job must keep its own immutable snapshot if the set is edited later.

Recommended storage module `workspace_store.py`: bounded validated JSON, atomic writes, schema version, UUID-style safe IDs, no user-supplied file paths. Prefer one file per set and one file per batch under an application data directory. Invalid or interrupted files must not hide every valid set. Deleting a set must not delete evidence runs.

Suggested API surface, to be finalized by the commander:

| Route | Purpose |
| --- | --- |
| `GET /api/live/prompt-sets` | List saved sets and prompt summaries |
| `POST /api/live/prompt-set` | Create/update a bounded set using a validated ID |
| `POST /api/live/prompt-set-delete` | Delete only the named set, with intentional UI action |
| `POST /api/live/batch` | Run selected saved prompt IDs with one attached model and a scan-policy snapshot |
| `GET /api/live/batches` | List durable batch state and result links |
| `POST /api/live/batch-stop` | Cancel exactly the expected active batch/job |

One model worker runs prompts **sequentially** to control GPU memory. The user can prepare many prompts and start one batch, but the UI must not call this simultaneous GPU execution. LiveService remains the single lock/job owner: avoid having a second queue thread call `start()` while another user action is active. The batch coordinator calls the same base/collect primitives and records each child result, then proceeds to the next item. Cancellation stops further prompts and preserves completed evidence.

A prompt's generated length is unknown at queue creation. Batch scan policy should represent a whole-trace endpoint symbolically (for example `end: null`) and resolve it after that prompt's base is generated. Do not reuse the first prompt's numerical endpoint for every prompt. Explicit region overrides outside a generated trace should fail visibly for that item. Persist per-item `pending/running/complete/error/cancelled` with run IDs and a batch summary. On process restart, mark an interrupted active item as interrupted; do not silently pretend generation has resumed.

## Bigger runs and meaningful comparison

Expose two plain-language presets that still reveal the actual settings before launch:

- **Exploratory scan:** spaced checkpoints and a modest draw count.
- **Reference run:** every-token checkpoints over a chosen interval and a larger draw count. Show exact continuation count and maximum output tokens before execution. Do not make an expensive reference automatic.

The most useful path is: open a completed exploratory run → use its saved trace → configure a reference/refinement → run on the exact source model → compare. Generating a new base for a reference invalidates token-position comparisons even if the prompt text is unchanged.

New module `run_comparison.py` should compare saved records without changing fits or rerunning inference. Recommended POST `/api/live/compare`: two `{run_id, pass_id}` selections and, if useful, a named comparison mode. Return compatibility checks first, exact aligned token positions, per-position outcome counts and proportions, TVD and quality diagnostics, with reference uncertainty clearly labeled.

Strict same-trace comparison requires:

- Same model identity/revision, tokenizer identity and exact prompt/generated IDs.
- Same outcome labels/order and parser/readout semantics.
- Same continuation temperature, cap, branch temperature, top-k/threshold and resulting candidate distribution at compared positions.
- Compatible generation settings and provenance. Where earlier artifacts lack a field, mark it unknown rather than silently pass it.
- Separate draws for reference-style evaluation. Same run/pass selected twice must be rejected. Overlapping recorded seed coordinates need a dependence warning or held-out-metric refusal, rather than an independence claim.

Only compare matching **measured positions** for raw-to-raw TVD. Never zip arrays by index or equate a token position in two different traces. A fit can be evaluated at measured reference positions inside its recorded support, explicitly labeled fit-to-reference. Do not use interpolated reference values as observed truth. Report how many positions and draws contributed, and exclude no outcomes silently: show Other and token-cap counts separately. If incompatible runs are selected, show their descriptive summaries side by side with precise reasons metrics are withheld.

A cost ratio is only measured work/time for those configurations. It is not equal-accuracy savings unless the user has deliberately designed and evaluated that comparison. Comparisons across multiple prompt sets should remain per-prompt matched pairs; aggregating unmatched trace token indices is invalid.

## Proposed engineering ownership

| Owner | Files/responsibility |
| --- | --- |
| Commander | `live_service.py`, `microscope_server.py`, new workspace/comparison backend modules, durable state, package registration and endpoint integration |
| Model engineer | `live_model.py`, model preflight module/tests, `docker/autoload.py` and model defaults; report API contract before UI coupling |
| Experience engineer | New workspace UI/module/CSS, generic navigation, prompt-set editor and queue controls; existing `live.html`/`live.js` integration coordinated with commander |
| Evidence engineer or commander | Saved-run comparison UI and reference-from-source entry point; reuse graph primitives rather than fork estimator math |
| Mirage | Architecture/adversarial workflow audit, generic/public copy audit, acceptance review; no core edits until separately assigned |

No GPU runs, paid cloud resources, registry publishing or Git push are needed to implement and verify the local workflow. Those remain separate acceptance/deployment operations.

## Acceptance criteria for this turn

1. A fresh installation shows generic navigation, no personal Muse commit, no user-specific run IDs, no automatic download and no personal cloud credentials.
2. Every exposed primary button executes a real action or is visibly disabled with a reason; draft export remains explicitly a draft.
3. Preflight and attachment can distinguish native causal loaders, special Muse loading, missing CUDA, no chat template, unsupported custom code and missing model metadata. Tested support is distinguished from architectural eligibility.
4. A user can create two prompt sets, edit multiple prompts, reload the browser, reopen them, and choose which prompts to run.
5. A batch produces independent per-prompt base traces and child runs, handles differing trace lengths, updates progress and preserves completed runs after cancellation or one-item failure.
6. A source run can configure a larger same-trace job without asking the user to copy IDs or edit JSON; exact identity and settings are carried through.
7. Saved runs can be compared on aligned positions, with TVD and cap/readout diagnostics; mismatched models, traces, categories and sampling settings cannot produce misleading accuracy metrics.
8. Existing Muse evidence still loads, exports, imports, refines and renders the audited curves unchanged. Upstream estimator source remains untouched.
9. Tests cover queue state transitions, immutable queued snapshots, bad IDs/schema, different prompt lengths, cancellation, same/different-trace comparisons and preflight blockers. Browser QA covers fresh/empty state, saved state, responsive navigation, failures and disabled actions without downloading weights.
10. Release report states what was actually tested. Multi-model GPU validation, central hosted authentication/isolation, partial draw resumption and one-click provider provisioning cannot be called complete on the strength of mocked/unit tests.

## Product tradeoffs after implementation

- A single-worker queue favors predictable memory and reproducibility over concurrent GPU throughput. Multiple workers can be added behind the same batch schema later.
- Native Transformers integration supports many architectures with one adapter, but excludes popular quantized/chat-only backends unless their required capabilities are implemented.
- Strict comparison checks reduce misleading numbers but will reject some comparisons users expect. Descriptive side-by-side evidence remains useful when metrics are withheld.
- Presets shorten setup but do not guarantee a visible fork. Preserve their explicit sampling settings and uncertainty labels.
- Self-hosting avoids silently collecting users' keys and traces, but setup remains more involved than a central consumer SaaS. Honest installation instructions are part of the product, not a hidden workaround.

