# Product readiness pass — September 10, 2026

The interface is ready for local usability testing. This pass does not certify a public hosted service, all-model compatibility, or reproduction of Goodfire's model-specific efficiency claims. All changes are local; no new inference, pod, deployment or credential storage was used.

## Verified method

The released Goodfire code is pinned and unmodified. All 203 released store hashes/reference curves verified; four released-data reconstruction cases agreed exactly with upstream. Both real Muse fits reproduced within 1.2e-16, with the same candidate boundaries. The independent algebra and reference tests found no arithmetic defect. See [math audit](math-audit.md), [machine-readable evidence](math-checks.json), and [reproducible checker](check_math.py).

The application collects independent draws from the retained-branch mixture, using every outcome once. This is compatible with the paper's multinomial mixture formulation, but differs from collecting S continuations per branch. Headline savings and accuracy on the paper's tinyMMLU/8B models were not established for Muse. CV-selected boundaries are exploratory, not significance tests. Original/refined retained mass drops to 79.1%/83.7%, so this restriction is visible next to the graph.

## Implemented workflow

1. **Model → Question → Scan:** one setup stage at a time, actionable disabled buttons, real hardware availability, and expandable technical settings.
2. **Explore:** model, run, counts and selected outcome are visible above the graph; the long prompt is collapsed.
3. **Inspect:** original text alongside recorded continuations; outcome/completion filters, checkpoint keyboard navigation, copy text and clear empty states.
4. **Refine:** click a candidate interval, choose tighter spacing and more draws, keep the source cap, preview exact endpoints and projected runtime, restore the original IDs or export a portable worker job.
5. **Move evidence:** import/export completed JSON; atomically install new runs, verify raw graph/response agreement and source identity, never overwrite an existing different run. Imported fits carry a not-recomputed label.

The original celestial atmosphere remains subdued. Motion defaults off, remains optional and respects reduced-motion preferences. Text selection does not compete with drifting visual elements.

## Design decisions and tradeoffs

| Decision | Benefit | Remaining cost or risk |
| --- | --- | --- |
| Progressive setup stages | Smaller decisions and clear next action | Expert users make more clicks; advanced settings remain accessible |
| Graph and quality counts before raw text | A user sees what was measured before interpreting a branch | Summaries can over-dominate; raw counts and responses remain one click away |
| Candidate labels and retained-mass disclosure | Avoids confusing smoothing with significance or exhaustive coverage | More concepts to learn; method detail remains expandable |
| Outcome/completion filters | Quickly separates alternative replies from capped generations | Filters persist across checkpoints and may yield zero records; clear/reset action is visible |
| Explicit source-model matching and separate refinement records | Preserves comparison and provenance | Same pinned model and source evidence must exist on the worker |
| CPU preflight for default Muse | Avoids automatic large-model download to a CPU runtime | This is not a general model-memory estimator; GPU availability does not guarantee fit |
| Portable evidence import | Offline local exploration without manually moving folders | 64 MB browser limit; stored fitted curves are not independently recomputed on import |
| Loopback-only single worker | Existing private local workflow remains simple | No hosted authentication/multi-user isolation; do not expose this server publicly |

## Remaining release blockers to consider

- Cloud onboarding remains manual: provider credentials, hardware selection, deployment, storage, backups and pod teardown are not automated in the product. This conversation's operational automation was separate from the application.
- The latest controls are not published in the Docker registry or Git yet. The checkout has them; an updated tested image must be built before using them on a new VM.
- Editing a reasoning passage exports a draft; generating matched control/edit branches is not yet implemented.
- Long jobs save at branch boundaries, but cannot resume partial runs. No model-agnostic preflight guarantees output parsing or GPU fit.
- No first-time external user session has validated the onboarding; browser testing cannot replace this.

## Validation

- 76 upstream tests passed during mathematical audit.
- 100 application Python tests passed after integration (including archive roundtrip/conflicts, forged/malformed records, same-origin HTTP import, targeted cancellation and CPU guard).
- 10 JavaScript evidence/math/pass tests passed; changed modules pass syntax checks.
- Browser checks cover desktop/mobile, both real saved runs, exact counts, candidate→refinement→source setup return, outcome and cap filters, keyboard navigation, reduced motion, disconnected/empty states, and no accidental model POST.
- Integrated browser QA additionally verified exact source-token job export, malformed-file rejection and idempotent real-run import with no inference calls. Screenshots are saved as desktop.png and mobile.png.
- No real GPU generation was repeated for GUI changes. Live worker execution of the updated interface remains a subsequent acceptance test.

More detailed UI notes: [observatory](observatory-ux.md), [setup](setup-ux.md).
