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
