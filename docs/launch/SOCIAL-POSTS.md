# Launch copy — drafts for Isaiah to review

These posts have not been submitted to either platform. Use the final public GitHub release after CI passes. The screenshot is actual application evidence; do not describe it as a newly discovered causal mechanism.

## LinkedIn

I've been building Fork Microscope: a research workbench for exploring where a model's possible answers change along a generated response.

It grew out of a practical question: once a graph points to an interesting part of a response, how do you inspect the actual continuations, sample that region more closely, and keep the comparison reproducible?

The workflow is:
• Connect your own local or GPU-VM worker and load a supported model.
• Enter a prompt, choose the answer labels to track, and sample checkpoints.
• Read the recorded continuations alongside raw frequencies and fitted estimates.
• Reuse the exact original trace for a closer scan, then compare compatible evidence.

The underlying method comes from Goodfire's Forking Fast. My contribution is the application and investigation workflow around it. I used AI coding agents to help build and review the implementation.

This is an early research beta, not a claim that a graph reveals the model's internal causal mechanism. You bring your own compute, and model support is intentionally bounded.

I'm looking for a few people working on LLM evaluation or interpretability to try a small run and tell me where setup or evidence inspection gets confusing. Model compatibility reports are especially useful.

GitHub: https://github.com/iPolluxx/fork-microscope
Dashboard: https://fork-microscope-wzyjs4vwsq-uc.a.run.app

## X — four-post thread

1. I built Fork Microscope: scan a model response at checkpoints, inspect the continuations, then sample more closely around an interesting region. A research beta built around Goodfire's Forking Fast. https://github.com/iPolluxx/fork-microscope

2. The workflow: connect your own worker → load a supported model → prompt → sample → inspect → refine → compare. Refinements reuse the exact original token sequence. The website provides the interface; you bring the compute.

3. Raw frequencies and fitted estimates stay separate. A change in the graph is a candidate for investigation, not proof of an internal mechanism. This is workflow tooling around existing research; I used AI coding agents for implementation and review.

4. Looking for early testers in LLM evaluation / interpretability. Try a small run and report setup friction, model compatibility or confusing evidence views. Hosted UI: https://fork-microscope-wzyjs4vwsq-uc.a.run.app

## Media and publishing notes

Use `docs/images/observatory.jpg` for a screenshot of the actual saved-run inspector. An honest caption: “Recorded continuations and outcome estimates from a Muse run; this example mostly chose DELAY.”

Publish after checking the GitHub release and instructions from a signed-out browser. Ask for specific early feedback rather than claiming universal model support, novel causal findings or proven compute savings. LinkedIn and X wording can be edited into Isaiah's voice before posting.
