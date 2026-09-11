# Saved prompt-set workspace

Implemented September 10, 2026. Owned files: `public/fork-microscope/workspace.html`, `workspace.mjs`, `workspace.css`, and this report. Existing app, model, comparison, server and estimator files were not edited.

## User flow

1. Create a named prompt set. Add up to 50 prompts, each with a stable UUID, title, exact prompt text, answer labels, chat/base format, original-response token cap and seed.
2. Save the set to the selected worker. Reopen it from the library or through `workspace.html?set=ID`. Unsaved edits are visibly marked and guarded when switching sets or navigating away.
3. Select individual prompts with Run checkboxes. Configure checkpoint spacing, total draws per checkpoint, continuation cap, temperature, retained top-k, minimum probability, scan seed and reconstruction tuning.
4. Run one immutable batch snapshot on the attached model. The UI explains sequential prompt execution and an independent original trace for each prompt. Run is disabled with an explicit reason when the worker is unreachable, no model is attached, another job is active, the set is unsaved, selection is empty or scan settings are invalid.
5. Inspect worker progress and durable batch/item states. Stop only a matching active batch's exact job ID. Open Explore/Compare only for items marked `complete`; assigned run IDs on incomplete items do not become broken result links.

Sets remain editable without a model. The page does not load models, create cloud resources, collect credentials or modify estimator math.

## Portability and worker separation

The page loads `/worker-connection.js` before its ES module and sends API traffic through `window.workerFetch` (same-origin fetch remains a fallback). Root's connection layer owns worker URL, authentication and stale-response rejection.

On `worker-connection-change`, the workspace clears saved-set/batch/runtime state. Existing prompt text becomes an unsaved new set with its previous set identity removed; saving it to the new worker is an explicit copy action. A persistent message describes this. Modal actions from the old worker close, and epoch guards discard stale responses. No set/evidence/credential data is written to browser localStorage.

Export downloads the current valid prompt set as `fork-microscope-prompt-set-v1` JSON. It does not silently save unsaved edits. Import accepts a valid export or a compatible `{set: ...}` API wrapper, ignores stored set ID/revision and extraneous properties, gives prompts fresh UUIDs, and creates a new set through the actual save endpoint. Import never starts model execution. UI imports are limited to 2 MB; backend validation is authoritative. Copy says to export before deleting a disposable worker.

## API integration

| Request | Expected response/use |
| --- | --- |
| `GET /api/live/prompt-sets` | `{sets:[...]}` with full prompt arrays |
| `POST /api/live/prompt-set` | `{id?,name,prompts}` → `{set:...}`; set revision and timestamp displayed |
| `POST /api/live/prompt-set-delete` | `{id}` → `{deleted:id}`; saved runs/history preserved |
| `POST /api/live/batch` | `{set_id,prompt_ids,scan}` → `{job_id,batch_id}` |
| `GET /api/live/batches` | `{batches:[...]}` with batch `state`, item `state`, optional item run IDs and errors |
| `GET /api/live/status` | `{model,job}`; current job uses `status`, not `state` |
| `POST /api/live/stop` | `{job_id}`; current job must match displayed batch |

Saved prompt links use `/live.html?set=SETID&prompt=PROMPTID`. Completed-run links use `/observatory.html?run=RUNID` and `/compare.html?left=RUNID`. Root/model/comparison owners integrate those destinations and static asset registration. Navigation is Workspace / Configure / Explore / Compare.

The UI currently supports the existing live field bounds: title/set name up to 120 chars, prompt text up to 16,000, 1–32 labels of up to 200 chars, original cap 8–4096, seed 0–2^31−1; spacing 1–128, samples 5–512, continuation cap 1–4096, temperature .05–2, top-k 1–50, threshold 0–1, CV/fixed tuning. Client answer checks catch common normalized duplicates; the worker's Unicode casefold/readout validation remains authoritative.

## Budget and evidence semantics

The budget is an upper bound using each selected prompt's original-response cap, not an assumed shared actual trace length. Checkpoint counts include the forced final endpoint:

`floor((cap−1)/stride) + 1 + ((cap−1) mod stride != 0)`.

The resulting visits × samples × continuation cap is maximum new continuation tokens. Copy explicitly excludes original generation and prefix processing and makes no runtime, dollar-cost, equal-accuracy savings or fork-discovery claim. The selected worker records actual generated lengths and scientific results.

Only `item.state === 'complete'` permits result links. Failed/cancelled/running items with assigned run IDs state that completed results are unavailable and any partial records remain on the worker. Stopping a batch preserves completed results.

## Checks actually run

- `node --check public/fork-microscope/workspace.mjs`: passed.
- Node assertions for valid/invalid prompt sets, labels, integer limits, duplicate IDs, scan limits, every Run-disabled reason, import identity stripping, and upper bounds: passed. Bounds included 512/32 → 17 checkpoints; short/off-grid 8/32 and 32/32 → 2; 33/32 → 2; every-token 33/1 → 33.
- Headless Chromium using installed Playwright at `http://127.0.0.1:8767/workspace.html`, with every API route replaced by a test worker: passed 12 workflow groups, no page exceptions. Covered empty/no-model state, creating two sets with multiple prompts, save/reload/reopen, unsaved guard, actual download event, selected batch payload, exact-job stop, complete-only links, import as a new set, delete preserving history, and worker-change isolation.
- Measured no horizontal overflow at 1440px and 390px viewports. Desktop grid measured 220px / 778px / 330px plus gaps; narrow layout stacks controls.

These browser checks used **mocked worker responses**, not real model execution or mutations of the user's saved prompt store. Root owns real endpoint integration, cross-origin authenticated worker QA, packaging and final validation. Multi-model generation, cloud provisioning and production concurrency are not certified by this UI work.
