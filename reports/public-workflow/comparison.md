# Same-trace scan comparison

Implemented files: `run_comparison.py`, `test_run_comparison.py`, `public/fork-microscope/compare.html`, `compare.mjs`, `compare.css`. API/static integration is owned by the coordinating agent. No inference or reconstruction runs as part of a comparison.

## Backend contract

`compare_runs(left_raw_export, right_raw_export, left_pass_id, right_pass_id)` returns JSON-serializable `schema_version: "run_comparison.v1"` with:

- `selection`: the four selected run/pass IDs; `created_at`: report timestamp.
- `compatible`, `reasons`: failed identity/settings checks. Incompatible reports contain no comparison metrics or overlays.
- `categories`: the exact shared outcome order.
- `left`, `right`: selected pass label/model/revision, verified `observed` rows `{t,samples,counts,values,retained_mass}`, validated saved `fit` rows `{t,values}`, `fit_note`, checkpoint coverage, sample count range, collected draws, generated tokens, collection seconds, cap hits/fraction, Other count/fraction, and retained probability mass range.
- `raw_shared`: shared-position rows with TVD, sample denominators, retained-mass difference; mean/max TVD and count; exclusive checkpoint lists. No overlapping checkpoint means unavailable/null, not a score of zero.
- `fit_to_observed.left_fit_to_right` and `.right_fit_to_left`: TVD only at actual measured comparison checkpoints that were **not training checkpoints of that saved fit**, lie inside its observed range, and have a valid saved fit value. Each direction includes evaluated rows/count/mean, exact excluded positions grouped by reason, comparison-run sample count range, and whether every reference point has more draws than every fitted-scan point. Differing recorded library versions withhold both directional scores with `withheld_reason`, while raw descriptive TVD remains available. Dense references can be selected as `dense`; they have observed points but no fitted curve.
- `provenance`: same-run metadata for eligible comparisons; duplicate observations are rejected before scores; overlapping next-token allocation seeds and generation-batch seeds; complete/incomplete seed evidence; source/replay lineage; shared original trace; explicitly no automatic independent-reference claim.
- `caveats`: interpretable scope, reference uncertainty, sampling/selection limits, cost accounting and readout caveats.

The server endpoint is `POST /api/live/compare` with exactly `{left_run_id,left_pass_id,right_run_id,right_pass_id}`. The service loads both raw exports; the request cannot supply synthetic observations to this endpoint. The response may be exported by the browser for review.

## What can and cannot be compared

Require exact saved prompt and original-response token IDs, pinned model identity, matching recorded dtype/architecture/vocabulary, categories, explicit parser version, original prompt/format/answer tracking, sampling design, temperature, candidate top-k, threshold, continuation cap/effective sampler, and generation defaults. Hub models require the same model ID and immutable-looking resolved revision (40–64 hex characters). Local snapshots with equal `local-sha256:<64 hex>` content fingerprints may have different worker paths; `same_model_identity` enforces the shared preflight identity contract. Counts and checkpoint spacing may differ. This deliberately rejects cross-model/tokenization comparisons and unverified legacy weighted records rather than aligning unrelated token positions.

Every checkpoint's counts are recomputed from saved labels with unique draw indices and complete coverage. Candidate token IDs/probabilities must be present and sum to retained mass within absolute tolerance `1e-5`. At shared checkpoint positions, candidate ID sets must match and each candidate probability must agree within `1e-5`; otherwise the compared mixtures are incompatible. This only verifies shared measured positions, not unmeasured positions. Invalid/missing records produce reasons. Saved reconstruction input proportions must agree with those verified observations; otherwise the fit is excluded while raw counts remain usable. Malformed, duplicate or unsupported fitted positions are excluded without interpolation or extrapolation. The Goodfire reconstruction algorithm is not rerun or replaced.

The raw score is `0.5 * sum(abs(left_category_fraction - right_category_fraction))`, averaged equally over shared checkpoint positions. It is a descriptive finite-sample difference across all labels, including Other. No p-value, guarantee, or mechanism claim is made. Fit-to-reference scores compare a saved estimate with a new measured checkpoint, not with hidden true probabilities. Both the fit and the reference can be noisy. Library/hardware differences and retained-mass changes receive caveats.

A source/refinement relationship does not establish independence. Next-token allocation seeds and the actual adapter's per-batch generation seed derivation are checked when fully recorded. Distinct decisions support separate sampling but do not establish independent tasks or erase selection after looking at the first run. The same run/pass or an identical saved observation record is rejected with metrics withheld; a tautological zero is not displayed as replication. Seed reuse is explicit for otherwise eligible comparisons. Shared checkpoint positions are excluded from directional fit evaluation even if a new run generated fresh draws there, making the evaluation focus on previously unsampled positions.

Collection cost is shown per selected pass: observed number of draws, generated tokens and recorded collection wall time. Model download/load, replay, deployment and other passes are not included. Differences in coverage, samples or hardware do not demonstrate savings at matched accuracy. Missing completion/token/time metadata is displayed as unavailable, not zero.

## Static dashboard and worker routing

The page loads `worker-connection.js` before `compare.mjs`, uses `window.workerFetch` for all API operations, and resets stale evidence on `worker-connection-change`. Models, saved archives and computation remain on the user's local/VM worker. Connection configuration is handled by the shared worker widget, not duplicated on this page.

`?left=RUN_ID&right=RUN_ID` hydrates initial selection; `?run=RUN_ID` is accepted as a left-side fallback. Each side lists its available passes and optional dense reference. Explore links preserve run identity. Buttons refresh the library, request a report, and export the actual returned report. Output/category, saved-fit visibility and shared-coverage controls change the graph without new math requests. Worker changes clear the old report.

The page includes same-trace and same-evidence rejection reasons, denominators, source summaries, exact excluded reference positions, keyboard-operable controls, descriptive SVG labels, a data table and a responsive dark layout. The selected original model trace is not exposed as a fictional universal token coordinate.

## Verification so far

- Twelve CPU tests cover known zero/nonzero TVD, settings/trace/model/parser mismatch, verified local snapshots across worker paths, candidate distribution/metadata checks, library-version mismatch with fit-score withholding, differing sample counts/spacing, no overlap/support, lineage with incomplete or overlapping RNG provenance, self-comparison, invalid/missing draws, nonfinite values, capped/Other outcomes, inconsistent saved fits, dense reference selection, and input immutability.
- Read-only comparison of the two latest actual matching Muse source/refinement archives succeeded. It found two shared checkpoints and 14 new measured refinement positions for evaluation of the original coarse fit; reverse evaluation was correctly unavailable after exclusions. This verifies plumbing on stored data, not a new experiment or novelty claim.
- `node --check compare.mjs` passed. Browser validation is recorded below when completed. The first attempt against the shared 8767 server used its old running code before the coordinator's planned restart; no shared server was stopped or restarted by this worker.
- Isolated Playwright fixture checks passed: query selection, known score, JSON export, graph controls, mobile width, self/incompatible cases, empty library and worker-change reset. No model calls ran; the fixture server was separately created and closed by the test.

- Real 8767 browser validation passed after the coordinator restarted the worker: expected actual archive scores (2 shared positions, 14 new reference positions), comparison JSON download, mobile width, and return to the exact source run. Only `/api/live/compare` received a POST; no model or run call was made. Screenshots are `/tmp/fork-comparison-actual-desktop.png` and `/tmp/fork-comparison-actual-mobile.png`.
- Final browser guard checks used cloned actual archives with mocked comparison responses: self and sampling-setting mismatch hide all metrics; library-version mismatch keeps raw descriptive scores and explains withheld fit scores. No saved archive was mutated.
- Mobile graph coordinates adapt to the actual container width, keeping tick labels legible instead of shrinking a desktop SVG. A final actual-archive mobile chart check passed at 390px without page overflow; chart screenshot: `/tmp/fork-comparison-mobile-chart.png`.
