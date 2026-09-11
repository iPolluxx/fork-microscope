# Observatory product layout review

The saved-evidence experience now leads with the measured result and separates three actions: explore the outcome map, read checkpoint evidence, and configure a refinement. This is an interface improvement, not a claim that the entire product is commercially ready.

## Implemented

- Persistent navigation between saved evidence and model/run setup; import/export beside an identifiable saved-run selector.
- Visible collection summary: checkpoints, draws, finished responses and token caps. Outcome counts remain separate from completion counts. Counts reflect the selected pass and aggregate checkpoint draws; they are not independent experiments.
- Original prompt collapsed by default, with a readable preview. Full settings stay on the setup page. Denser sampling settings are a deliberate expandable step below the graph.
- Wider graph and selected checkpoint controls, accessible candidate interval buttons, keyboard-operable graph dots, raw/fit legend, optional point intervals and explicit sampling coverage. Fit regions are labeled candidates, never significance or causal claims.
- Adjacent original-prefix and continuation reader panels. Local filters for recorded outcome and completion show the number of matching draws at the selected checkpoint; filtered empty states explicitly offer clearing filters. Filters persist across checkpoint changes to support following rare outcomes.
- Clear final-reply/new-text/full-response views and a copy-text action. The optional replacement draft remains explicitly unexecuted and separate from recorded evidence.
- Source-parent link falls back to saved replay-verification provenance for historical refinements.
- Stronger foreground contrast, flatter glass surfaces without backdrop-blur rendering artifacts, static atmosphere by default, system reduced-motion support, narrow-screen stacking and contained horizontal graph scrolling.
- Helpful empty-library and load-error states, retry and setup/import actions.

## Advantages

The primary evidence is visible before the prompt and configuration forms consume the page. A new user sees what was actually collected, including caps, before interpreting fit geometry. Refinement is discoverable both in the graph and a separate labeled disclosure, without competing with the text reader. Exact outcome wording and source text stay available; no new semantic summaries are invented. Inspecting rare outcomes requires filtering saved text rather than manually scanning twenty dropdown entries.

## Tradeoffs and remaining limitations

- The graph, source text and sampling terminology still require a short onboarding example. A polished layout alone cannot make experimental design self-explanatory.
- A single-outcome plot preserves legibility but makes comparing the full outcome distribution slower; the outcome chips switch the plotted category. A later comparison mode should preserve raw evidence and clearly distinct colors.
- Raw Wilson point intervals are wide at twenty draws. They are useful uncertainty cues, not a significance test; users must open method details for interpretation.
- Two-column inspection saves comparison effort on desktop, while mobile necessarily separates source and continuation vertically. A future source-peek control could reduce scrolling.
- At many hundreds of checkpoints, wrapping token buttons becomes inefficient; a virtualized checkpoint list or searchable token navigator would be appropriate. The current 16-checkpoint result is comfortable.
- Outcome filters apply to the selected checkpoint, not every continuation in the run. A later global search needs explicit checkpoint context and reproducible export of the selection.
- Refinement and edit execution still depend on an attached compatible worker. Edit drafts do not execute interventions. Deployment, authentication, model compatibility and statistical validation remain separate readiness requirements.
- Larger passage/context preferences, remembered layout and comparison of parent/child distributions are useful additions after validating this flow with users.

## Validation

Browser checks cover the real 320-draw saved refinement and source run, outcome counts, filters, empty filter state, draft navigation, keyboard checkpoint selection, refinement disclosure and exact interval fill, mobile containment, no client script errors and reduced motion. Screenshots retained in /tmp/observatory-product-desktop.png and /tmp/observatory-product-mobile.png for review. No GPU runs were started for interface validation.
