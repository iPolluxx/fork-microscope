# Public workflow implementation — September 10, 2026

The application now supports a separately hosted static dashboard connected to an individually owned model worker. Mirage reviewed the architecture, the model/workspace/evidence engineers implemented separate components, and the commander integrated the API, queue, worker connection, packaging and verification.

## User journey implemented

1. Open the dashboard and connect a local or HTTPS/SSH-forwarded GPU worker with its worker token. The single installation view remains usable directly on localhost.
2. Inspect a native Hugging Face model or a local safetensors directory. Inspect checks architecture/tokenizer/context/metadata and estimates weight memory where metadata permits. Load is explicit; defaults select no model.
3. Create named sets with multiple prompts and answer labels. Save, reopen, edit, delete, export or import them. Opening one in Configure fills the question without generation.
4. Select saved prompts and choose checkpoint spacing, draw count, cap and sampling settings. One attached model executes prompts sequentially. Each item owns an immutable prompt/config snapshot and an independent original trace. Different trace lengths produce different endpoint-inclusive grids.
5. Explore completed evidence and the original Goodfire reconstruction. Inspect raw counts, retained mass, cap hits and generated continuations. Open a candidate interval or the whole original trace, choose refinement/reference settings, review the continuation budget and generate fresh samples from restored original IDs.
6. Compare two saved passes. The app checks trace, model, parser, sampling settings and candidate distributions. Duplicated observations and incompatible runs do not produce comparative metrics. Raw shared-point TVD and saved-fit versus new measured positions are distinct. Changed library versions withhold fit-reference scores. A larger reference remains noisy.
7. Export evidence and prompt sets before terminating disposable hardware. Completed items survive stop and restart; partial sampling does not automatically resume.

## Verification performed

- **146 Python tests passed** on the host and in the rebuilt CUDA container on CPU.
- **10 JavaScript graph/math tests passed** on host and in the container.
- Model UI: nine mocked browser workflows. Workspace: twelve mocked browser workflows. Comparison: fixtures and actual saved Muse evidence, export, mismatch/duplicate handling and mobile layout.
- Hosted transport: a dashboard and separately authenticated worker on different origins; saved prompt create/reload/hydration, session connection persistence, no-model disabled controls, authenticated evidence download and reference preset. No browser page errors. Desktop/mobile screenshots are retained here.
- Container startup: all four primary pages served; no model selected or automatically loaded; unauthenticated API returned 401; approved origin and bearer token returned worker status.
- New queue tests cover snapshots, differing trace lengths, cancellation, per-item failures and restart recovery. New identity tests allow identical local content at different worker paths and reject changed or unverified content.
- No inference ran on a GPU in this implementation turn. No cloud resources were provisioned. Browser/queue tests do not certify every native model architecture.

The audited reconstruction implementation and upstream pin were retained. Existing saved runs were read, not rewritten. The full mathematical audit remains in `reports/consumer-readiness/math-audit.md`; preserving that estimator does not establish universal fork accuracy or equal-accuracy compute savings.

## Build artifacts

- Local container: `fork-microscope:public-workflow`, image ID prefix `62bf3c0a0f93`.
- Static assets: `dist/dashboard/`, with an explicit file/hash manifest.
- Static upload archive: `dist/fork-dashboard.zip`.
- Hosting and worker setup: `docs/HOSTED-DASHBOARD.md`.

The container includes the application source at its build time. Subsequent documentation/static-archive convenience changes are present in the checkout; no Git commit, registry push, GCP deployment or visibility change was performed. The old published image remains a different source revision.

## Tradeoffs and remaining release gates

- One owner per worker gives simple ownership and predictable memory; it is not account-level isolation for unrelated users sharing one backend. Visitors can share the static website while using separate workers.
- The browser connector is real. Provider VM creation, SSH credentials, private model login and storage mounting still happen on the user's hardware/provider. Browser restrictions can block hosted-to-local requests; the same dashboard is served on the worker as a fallback.
- Native Transformers models are the supported route. GGUF/Ollama, generic chat APIs, quantized/custom-code checkpoints and arbitrary architectures require additional adapters. Hardware/parser smoke tests on more model families are still needed.
- Whole-file local model hashing takes I/O time but avoids pretending that a directory path is an immutable model identity. Changing the model directory after loading is unsupported.
- Large runs can still be expensive. Preview counts are budgets, not measured completion-time guarantees. Existing timing projections depend on comparable hardware and generated lengths.
- Edited-token drafts remain explicitly unexecuted. This work does not add activation interventions or automatic partial-draw resumption.
- The pinned upstream Goodfire checkout has no LICENSE file. Public redistribution of a bundled worker/image remains unresolved, as recorded in `THIRD-PARTY.md`. Static packaging excludes that Python code and dataset. Resolve project/upstream distribution permissions before declaring a complete public open-source release.

Supporting reports: `MIRAGE.md`, `MODEL-ATTACHMENT.md`, `workspace.md`, `comparison.md`, `ARCHITECTURE-AUDIT.md`, `hosted-qa.json`, `container-qa.json`.
