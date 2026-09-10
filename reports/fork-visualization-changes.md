# Fork visualization: evidence before reconstruction

Implemented September 9, 2026. No reconstruction mathematics changed.

## Behavior

- Outcome selector initially opens the most observed answer across the saved passes. The Muse pilot opens `no` instead of an all-zero `yes` category.
- Observed dots remain primary. A sparse, constant run (fewer than four checkpoints and identical distributions) initially hides reconstruction; the user can explicitly enable it. The actual Muse pilot therefore shows three observed 100% `no` dots, not a smooth bend mistaken for evidence of a fork.
- Optional 95% Wilson point intervals are on by default, only when actual saved mixture counts, per-checkpoint sample totals, categories and plotted proportions agree. At 5/5, this interval extends down to approximately 56.6%; 100% observed is not certainty about the underlying distribution. Legacy weighted proportions do not receive binomial intervals.
- Reconstruction uses dashed lines and distinct hover text. Optional nominal 90% fitted marginal bands remain visually separate from point sampling intervals. Invalid values create plot gaps; withheld fits and out-of-support values do not display as reconstruction.
- Segmentation intervals shade the space between their two observed endpoints. They require a valid fit and at least four valid checkpoints; explicit `segmentation_enabled=false` suppresses them. Older saved records fall back to the same checkpoint/fit checks. Midpoints are not displayed as exact causal tokens.
- The interval inspector prioritizes actual fitted boundaries and then ranks other adjacent observed differences by full-distribution total variation. These latter intervals are descriptive differences, not statistically established or causal forks. No significance threshold is invented.
- Selecting an interval shows the additional original tokens preserved at the right checkpoint: `tokens[left:right]`. Buttons open either endpoint's continuation library or zoom the graph to that interval. Graph dots still open their actual saved checkpoint; users can reset zoom.
- Empty/no-change states explicitly retain the possibility of changes in unsampled gaps. Completion/readout warnings and independent-reference comparisons remain available.

## Files

- `public/fork-microscope/live.js`
- `public/fork-microscope/live.html`
- `public/fork-microscope/live.css`
- `public/fork-microscope/graph-evidence.mjs`
- `test_graph_evidence.mjs`

Parent integration: add `graph-evidence.mjs` to the server static allowlist; include the dedicated JS test in CI. Parent already added reconstruction metadata to the backend.

## Checks

`node --check public/fork-microscope/live.js`

`node --test test_math.mjs test_graph_evidence.mjs`: 10 passing tests. Coverage includes sparse constant results despite bent smoothing/stale boundaries, explicit disabled/withheld segmentation, malformed/nonfinite/missing observations, malformed bands, no extrapolation, verified mixture counts, and nonzero uncertainty for 5/5.

Browser integration verification is assigned to the parent agent after the new module is allowed by the server.

## Limits

The interface does not establish causal mechanisms or statistical significance. Point intervals are per-outcome/per-checkpoint, not simultaneous bands and not change tests. Both observed proportions and intervals condition on the run's retained-branch sampling procedure and matcher. Fitted bands have a different model-based interpretation. All candidate intervals require inspecting actual saved responses and, for reliable claims, further sampling/interventions.
