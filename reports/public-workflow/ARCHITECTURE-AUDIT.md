# Mirage final architecture audit

September 10, 2026. Reviewed the current native model attachment, saved prompt/batch pipeline, remote-worker access, static dashboard transport and hosting instructions. This is a code/contract audit, not a penetration test or multi-model GPU validation.

## Architecture that is now coherent

The public website serves static application assets. Every user selects an independently owned Fork Microscope worker that owns their model, jobs, prompt sets and evidence. The dashboard is not a central GPU service and the worker is not a multi-tenant service. This separation matches the clarified product direction.

The remote worker requires a strong configured bearer token and explicit hosted origins. Its API routes enforce authorization, the browser sends the token as a header, and cross-origin preflight is limited to allowed origins. Worker switching invalidates transport responses and resets the selected evidence/model state. Loopback-only operation retains its simple local workflow. The docs correctly require an HTTPS proxy or SSH tunnel for VM access and disclose browser local-network permission limitations.

Saved prompt sets have bounded schemas, safe IDs and atomic JSON writes. A batch snapshots selected prompt contents, model metadata and scan settings. Execution remains sequential on the one attached model, so it does not falsely promise parallel GPU capacity. Each prompt receives its own generated base, actual trace-length resolution and unique child run. Cancellation preserves completed children, and restart marks incomplete items interrupted rather than fabricating resumption.

Larger reference/refinement runs restore the existing trace. Comparison remains a descriptive same-trace analysis with model, parser and sampling checks. The Goodfire fit source was not replaced by the orchestration work.

## Findings addressed during this review

1. **Local model portability:** a model moved from one worker path to another was previously rejected despite identical bytes. Added `model_preflight.same_model_identity`, used by `replay_trace`. Full `local-sha256:<64 hex>` equality allows relocation; changed, malformed or missing content identity fails. Repository/revision equality remains required for Hub assets. The commander and comparison engineer are integrating the same predicate at their respective boundaries.
2. **Batch allowance underestimated endpoints:** the original frontend formula omitted the forced final off-grid checkpoint. For a 512-token cap and spacing 32 it reported 16 instead of 17 checkpoints. The workspace engineer corrected the formula to match backend endpoint inclusion.
3. **Stop action used an untargeted payload:** Configure originally posted `{}`. The commander changed it to the currently selected job ID, matching batch/refinement cancellation behavior and preventing an old UI from stopping a replacement job.

## Validation from this audit

- 35 model/preflight/identity/replay tests passed after adding portability checks.
- 31 focused workspace, worker authorization, preflight and replay tests passed together.
- The existing HTTP integration test verifies allowed-origin authenticated status and prompt writes, denied unauthenticated and blocked-origin requests, and allowed preflight handling without loading a model.
- `git diff --check` passed.
- Earlier model UI validation included nine mocked desktop/mobile flows and explicitly one intentional mocked Load action; no real inference was performed in this review.

## Release claims and remaining limitations

No additional blocker was established for the **single-owner worker plus public static dashboard architecture** by this review. This does not certify a central shared worker, broad model-family generation behavior, hardened internet-facing server operation or completed deployment.

Native loader eligibility must remain separate from model validation. The adapter requires real token/logit access and standard generation; it does not implement ordinary chat endpoints, GGUF/Ollama, custom model code, quantization, multi-GPU loading or MPS. Metadata alone cannot validate model-specific EOS behavior or answer extraction. A short real run is still required for each intended model family.

The Python worker should remain private behind the documented SSH/TLS setup. Its bearer token grants owner-like access to that worker; there is no per-user permission system inside one worker. Library-version and retained-mixture differences are disclosed in saved-run comparisons, which should not be presented as guaranteed equal-distribution accuracy benchmarks. Partial sampling is retained but not resumable. Editing exported token drafts still does not execute a text intervention.

Those limitations belong in the release notes and onboarding. They should not be hidden by labeling the current checkout as a finished universal consumer service.
