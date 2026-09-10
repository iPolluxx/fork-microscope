# Reviewer benchmark reproduction

`review-reproduction.json` was generated on CPU by:

```bash
.venv/bin/python scripts/benchmark_review.py 40 outputs/review-reproduction/benchmark.json
```

The script adapts the reviewer-provided `fork-microscope-twogrid-bench.py`. It uses released data, not newly generated Muse responses. It reproduces the reported numbers to four decimal places.

At strides 4, 8, and 16, separate offset fits have mean TV 0.0303, 0.0349, and 0.0408, versus 0.0280, 0.0304, and 0.0350 for the half-stride uniform grid. Joint fits give 0.0280, 0.0304, and 0.0347. Lower TV is better for this metric. This supplies no evidence of an offset advantage under the tested settings.

These are not exactly matched token budgets. Endpoint counts can differ, and expected continuation lengths vary by position. The JSON includes each arm's actual draw count and expected generated-token budget per row so the differences can be inspected. All positions are scored, including extrapolation beyond each grid's edge; the current live UI only displays fits within sampled support. The double-S arm uses two overlapping blocks; other arms use three non-overlapping blocks. Comparisons aggregate within a row before comparing rows.

Reference outcomes use per-branch draws 90:200. Mixture inputs consume no more than the first 90 per-branch draws. There is no reference contamination by those input observations. This remains one model, fixed M5a settings, five outcome categories and a TV metric. No adaptive policy, held-out model generalization, matched-accuracy savings, or new reasoning mechanism is established. The independent-pass interface is a configurable measurement tool, not a claim that two passes are preferable.

## Application workstreams — 2026-09-09

[Integration and validation](integration-2026-09-09.md) links the implemented loading and graph improvements plus the proposed probe workflow.
