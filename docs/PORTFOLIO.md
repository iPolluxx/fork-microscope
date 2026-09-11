# Fork Microscope: research tooling as a product

## The problem

Checkpoint resampling produces a lot of evidence: generated traces, alternative continuations, extracted answers, raw counts, fitted curves and compute settings. A plot alone does not make that evidence easy to investigate. Researchers need to move from an interesting interval to closer measurement without losing the original trace or confusing an estimate with an observation.

## The implemented workflow

**Workspace → Configure → Explore → Refine → Compare → Export**

The workbench connects a separately hosted website to a user's own worker. It supports custom prompt/answer sets, model preflight, explicit sampling budgets, saved exact token sequences, interval refinements, recorded continuation browsing and compatibility-checked comparison.

![Actual saved Muse run shown in the observatory](images/observatory.jpg)

This screenshot is an actual collected run, not a mock result. The visible response overwhelmingly chose `DECISION=DELAY`: small deviations in that example do not establish a robust causal fork. The artifact demonstrates the collection and inspection workflow without turning a modest result into a research claim.

## What I contributed

The project grew from my effort to turn interpretability papers into tools people can use. I selected the workflow and research questions, tested the interface against actual runs and iterated on how the evidence is presented. I used AI coding agents for implementation and review; this portfolio does not claim that all implementation was written unaided.

Goodfire's Forking Fast provides the underlying research and estimator. My contribution is the surrounding application and reproducible investigation workflow. No new internal interpretability mechanism or superior sample-efficiency result is claimed.

## Engineering decisions

| Decision | What it gives the user | Tradeoff |
|---|---|---|
| Hosted static dashboard + personal worker | Users choose their hardware and keep data there | Users still install and connect a worker; no automatic cloud provisioning |
| Exact token IDs and pinned model identity | A refinement reuses the actual original trace | Library/hardware changes can still affect generation |
| Raw observations alongside saved fits | Users can distinguish measured frequencies from estimation | Uncertainty and labels require explanation |
| Compare only compatible evidence | A plausible-looking score is withheld when the experiment contract fails | Not every pair of saved runs can be compared |
| One owner/job stream per worker | Predictable model memory and simple data ownership | No multi-tenant backend or concurrent independent users on one worker |
| Native adapters with preflight checks | Early feedback on formats and memory | It does not support every model or certify all eligible models |

## Verification and limits

The beta adds a connection launcher tested for token generation, allowed origins and loopback binding. The existing app has CPU tests for sampling, extraction, replay, storage, authentication and comparisons, plus frontend math/pass checks. CI runs them from a fresh checkout and verifies pinned upstream tests/data. Numerical integration checks are documented in [the math audit](../reports/consumer-readiness/math-audit.md).

Prior Muse GPU runs demonstrate actual collection and saved-trace refinement. They are not a fresh GPU acceptance run of every release or a compatibility certificate for arbitrary models. Token-edit drafts are not executable interventions; activation probing and automatic partial-draw resumption are not implemented.

## What useful feedback looks like

The first users can help answer concrete product questions: Can they attach a supported model without assistance? Can they explain what a raw point means? Can they find and read the observations behind it? Can they refine an interval and compare only the evidence that is actually comparable?

The next improvements should follow those observations. This is a tool-building contribution around existing research, with clearly bounded claims.
