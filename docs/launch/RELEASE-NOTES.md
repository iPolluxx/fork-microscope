# Fork Microscope v0.1.0-beta.1

A research workbench for exploring where model outcomes change along a generated response, built around [Goodfire's Forking Fast](https://github.com/ericb-goodfire/forking-fast).

[Open the dashboard](https://fork-microscope-wzyjs4vwsq-uc.a.run.app) · [Install your worker](https://github.com/iPolluxx/fork-microscope/blob/main/docs/GETTING-STARTED.md)

**Scan → inspect recorded continuations → refine an interval on the exact original trace → compare compatible evidence.** Save prompt sets, run sequential batches and export evidence from your own hardware.

The website hosts the interface. Users provide a local/VM worker and model. The connection launcher prints a worker URL and generated token; it does not start a model or generation job. Linux x86-64 checkout installation is the tested path.

This is an early research beta. A fitted change is not proof of an internal causal mechanism. The current answer matcher detects mentions, and a finite reference remains uncertain. Native model eligibility does not guarantee every architecture/hardware combination works. Executed token edits, activation interventions and automatic VM provisioning are not available.

Release artifacts contain this project's static dashboard and license notices only. No GPU image, model weights, personal run records or upstream Goodfire code/data are bundled. This project's MIT license does not relicense third-party material; see THIRD-PARTY.md.

Feedback wanted: setup friction, supported-model reports, answer extraction failures, and whether the evidence-to-refinement workflow helps your investigations. Please include model/revision and hardware, never tokens or private prompts.
