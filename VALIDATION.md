# Validation scope — September 8, 2026

Environment: Linux x86-64, Python 3.13.13, uv 0.11.2, PyTorch 2.11.0+cpu, Transformers 5.16.1. The dependency locks record the remaining versions. `OTRECON_FORCE_RUPTURES=1` selects the reference segmentation implementation to avoid unverified acceleration differences.

Completed checks:

- Fresh recursive Git clone: `./scripts/setup.sh cpu` installed into a new virtual environment; all 34 repository Python tests and three JavaScript tests passed. The installed CLI served the dashboard assets and API successfully over loopback, including a same-origin model-control request.
- Upstream: 76 Python tests passed. All 203 released stores match their SHA-256 manifest; the released reference outcome curve recomputes exactly.
- Upstream numerical gate: both tracks' reference TV values/slopes and the deterministic-outcome gate passed. This is the upstream validation gate, not the full replicate-fan benchmark.
- Real CPU inference: the pinned SmolLM2 smoke profile generated a base, sampled both offset grids and an independent dense reference (56 continuations total), fitted both curves with cross-validation, calculated comparison metrics, and saved inspectable records.
- Muse preflight: downloaded the pinned configuration and processor, constructed its native chat prompt and an empty-weight `MuseGlimmerForConditionalGeneration` model, and verified end-of-turn/channel token availability and single-token A–D labels. No Muse weights were loaded.
- Repository tests exercise branch-based budgets, weighted outcome math, cross-validation, held-out comparisons, invalid configurations, Muse completed-answer extraction, and integer token IDs from the native chat template. JavaScript math tests cover grid costs and invalid inputs.

Still to validate on the VM: CUDA execution, full Muse weights, peak GPU memory, throughput, complete Muse answers, and the full Muse sampling run. The CUDA dependency set was resolved and pinned; the available local machine has no NVIDIA GPU. Do not interpret the CPU smoke settings or empty-weight preflight as evidence of Muse research quality.

Results are sensitive to tokenization, native chat template defaults, model version, numerical precision, sampling settings, batch size and truncation. Saved records preserve the exact prompt IDs, base IDs and generation configuration. Cross-device bitwise reproducibility is not promised.

## Schema 2 / configurable passes (2026-09-08)

These changes use direct position-level mixture collection: every generated observation is used once, with branch selection before generation. The live defaults are one pass; additional passes are optional. The old schema-1 results above remain historical evidence about the previous implementation, not validation of the revised sampling method.

- 42 Python tests pass, including a multi-branch collection/save/reconstruction/reference roundtrip, weighted branch selection, no duplicate/discarded draws, strict generic/Muse completed-answer extraction, alternate Muse EOS, independent pass plans, invalid config handling, and completion/short-grid gates.
- 5 JavaScript math/pass-model tests pass. A temporary jsdom harness also exercised default/add/remove pass tabs, independent settings, submitted payloads, saved-run opening, continuation viewing, and omission of fitted curves when withheld. No browser visual QA was performed.
- Real CPU run `8efc8894019b463c964f851309b8d4c2` produced 10 pass draws and 30 independent reference draws. All 40 hit the intentionally tiny 4-token cap, all were Other, no logit fallback occurred, and the fit/reference metrics were correctly withheld. This validates live generation and the new gate, not research quality.
- 76 upstream tests and 203 data hashes/reference round-trip pass. Upstream source remains unmodified.
- The reviewer-provided 40-question, fixed-parameter Llama replay benchmark was reproduced. The numerical artifact and budget caveats are in `reports/`.
- No VM or GPU was used for this update. Revised Muse GPU generation and container GPU inference remain untested. The previously built local container predates these changes; rebuild it before use.


## 2026-09-09 — Custom prompts and continuation library

- Added free-form prompt generation and 1–32 configurable answer texts, with versioned mention matching recorded in run metadata. Tracking answers do not alter the prompt. Case/whitespace-normalized whole-phrase matches, ambiguity, absent matches, capped replies and Muse/generic channel handling are covered by tests.
- Generalized live histograms, reconstruction and dense-reference comparisons to the record's category count. End-to-end deterministic fixtures exercise legacy five-category records and custom three/seven-category records with independent references.
- Local Python suite: 61 passing; JS math/pass suite: 5 passing. DOM interaction harness (temporary jsdom install, outside runtime dependencies) checks three-section navigation, prompt payloads, dirty prompt guard, independent passes, dynamic categories, pagination, search, completion filtering, raw text modes, literal HTML rendering and graph-to-checkpoint navigation. No browser visual inspection performed.
- Real offline CPU run: `292a15247c414bfe96d150c9a3993c58`, pinned SmolLM2-135M-Instruct, `configs/cpu-custom.json`. Base: “7 multiplied by 8 is 56.” completed. Two checkpoints, five draws each, 64-token cap: 10 continuations / 199 generated tokens / about 10.1 seconds collection. Outcomes: eight `56`, one `54`, one capped `Other`; no logit fallback. Small pipeline check, not a reliability or fork-detection result.
- No GPU or new cloud runtime was used. Muse-specific matching has protocol fixture coverage; these UI/readout changes have not been rerun on Muse GPU weights. Rebuild the Docker image to include this update before VM use.


## 2026-09-09 — Updated RunPod image

Rebuilt `fork-microscope:runpod` from `c08c79307d3383e473bb2eca6837684b32c8021f`. Container-side verification initially caught the missing Node executable used by the Python/browser parity test. Added the Node 22 binary from the official bookworm image, rebuilt, and verified 62 Python plus five JS tests pass inside the image. CPU startup/preflight, dashboard HTTP response, disabled model auto-load and results symlink were verified. No GPU allocation or model inference was performed for this packaging update.

Private image publication succeeded in workflow `34374004796` after freeing hosted-runner disk. Published tag: `ghcr.io/ipolluxx/fork-microscope:035d4da70050aa2c42c87ce173f7e3fd25a997d0`. Digest: `sha256:8705a302eb48ab569ce1dc07435131f2390d7bff42cf1b861a16481837e1d634`. The workflow verified package visibility equals `private`. Local CLI package inspection returned missing `read:packages` scope; no claim of a local authenticated registry pull is made.
