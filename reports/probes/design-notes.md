# Proposal: activation readouts beside behavioral forks

Date: 2026-09-09. Status: design and source inspection only. No installation, model download, GPU allocation, activation collection, probe training, or intervention was performed for this report.

## Recommendation

Build an **activation companion for saved checkpoints**, with a small supervised outcome probe as the first supported analysis. Keep the sampled outcome curve as the empirical measurement; put the probe's predictions in a separate, clearly named overlay. Use native PyTorch hooks on the model already attached to the app. This avoids loading another copy of Muse and does not require a new inference framework.

The useful question is: **Does a simple readout of a prefix's internal state predict its distribution of continuation answers on unseen problems?** A successful result would let a researcher compare behavioral changes with changes in a validated activation readout, then select places for deeper investigation. It does not establish that a readout dimension is a thought, that the model uses that dimension, or that a detected boundary causes a reasoning change.

The immediate shippable slice is capture, provenance, replay, and export. Training remains unavailable until a dataset contains enough independent problems and outcome variation. That is a data requirement, not a missing button to disguise with a prebuilt “thinking” classifier.

## What the app actually has

Inspected `live_model.py`, `live_service.py`, `outcome_readout.py` interfaces, the pinned environment, and saved run `live-runs/b242e31946994f65ad02ba1429aa140b`.

- `AttachedModel` owns the already loaded Hugging Face model. Muse uses `MuseGlimmerForConditionalGeneration` through `AutoModelForImageTextToText`, with its processor's tokenizer. The adapter uses evaluation mode and BF16 on the tested GPU.
- Raw pass records retain exact prompt token IDs, base token IDs, branch token IDs, continuation IDs, checkpoint positions, sample identities/seeds, completion status, and answer-matcher results. These can reconstruct the precise model inputs without re-tokenizing display text.
- Manifests retain the model revision, package versions, generation settings, and sampling design. The outcome curve is an estimate under the retained, renormalized branch distribution. It is not unrestricted sampling over the entire next-token vocabulary.
- The recent Muse run contains 74 prompt tokens, 380 base-response tokens, three sampled checkpoints (0, 128, 256), and 15 completed continuations. All 15 match `no`. **There are no activation tensors or trained probes in this record.** It can exercise replay/capture, but cannot demonstrate answer-class discrimination.
- Current service jobs are `load`, `base`, `run`, and `unload`. Collection and replay must share this single-job exclusion, so probes cannot attach hooks while another thread is generating or replacing the model.

The existing `logit_read_letters` is a final-layer next-token readout over single-token A–D labels. It is neither a trained activation probe nor a measure of eventual final-answer probability.

## Four different instruments

| Instrument | What it measures or changes | Appropriate interpretation |
| --- | --- | --- |
| Current continuation sampler | Frequencies of parser-defined outcomes after a prefix | Empirical behavior under the recorded sampling settings |
| Supervised linear probe | Predicts a supplied label/distribution from a frozen activation vector | Information accessible to this readout on its evaluation distribution |
| Logit lens / tuned lens | Projects intermediate states toward vocabulary predictions; a tuned lens learns layer-specific translators | Intermediate next-token readouts, not a substitute for continuation sampling |
| Activation intervention | Replaces, removes, or changes a specified internal value, then reruns the computation | Effect of that specific intervention on the measured outcome |

The tuned-lens paper and released implementation already cover layer-wise predictive readouts; rebuilding a generic lens dashboard would not by itself be a new method. [Paper](https://arxiv.org/abs/2303.08112), [implementation](https://github.com/AlignmentResearch/tuned-lens).

Probe accuracy can reflect what the classifier learns from correlations and lexical cues. Control tasks help reveal this problem; they do not convert a probe into proof of mechanism. [Hewitt and Liang](https://arxiv.org/abs/1909.03368).

## A crucial design constraint

For checkpoint `t`, define the pre-branch prefix as `prompt_ids + base_ids[:t]`. All continuations sampled from that checkpoint have the same pre-branch activation in a deterministic evaluation forward pass. Random draws do not provide different activation examples at that location.

Therefore, do **not** randomly split 40 continuations from the same checkpoint into training and test rows and report 40 independent feature examples. The feature row is the prefix; its target is the estimated outcome distribution. A probe cannot know which fresh random continuation will be drawn from an identical state.

A post-branch vector, computed after adding the selected branch token, is a different feature. It can predict branch-conditional outcomes, but carries the token identity itself. The MVP should use only pre-branch vectors; post-branch comparisons belong in an explicitly separate analysis with a token-identity baseline.

## Muse compatibility and collection specification

Verified the installed Transformers 5.16.1 source, rather than assuming a Llama-style wrapper. In the underlying Hugging Face model, the text block list is **`model.language_model.layers`**; in app code the full access begins at `AttachedModel.model`. Each `MuseGlimmerTextDecoderLayer.forward` returns its residual tensor after the MLP residual addition. The text model applies a separate final norm after the block loop.

The cached pinned configuration for revision `a4e59da52a7bc87ae7251dd5545c0dd437c44b68` has 52 text blocks, width 6656, and repeating sliding/sliding/sliding/full attention. The official model card corroborates that shape. [Muse model card](https://huggingface.co/meta-models/Muse-Glimmer-30B).

Proposed default capture:

1. Select zero-based blocks **12, 25, 38, 51** (rough depth coverage, not claimed privileged layers). Store their actual attention types; these four choices mix local and global blocks and do not isolate attention type from depth. A later attention-type study needs paired layers.
2. Capture the **last input position of each pre-branch prefix**. At checkpoint 0 this is the final prompt token, absolute index `len(prompt_ids)-1`. At checkpoint `t>0`, it is the final retained base token, absolute index `len(prompt_ids)+t-1`.
3. Register bounded forward hooks that copy only the selected `[batch, position, hidden]` rows, return `None` without modifying outputs, detach, and transfer those rows to CPU. Remove hooks in `finally`, including cancellation and failure paths. PyTorch provides the required module forward-hook API. [PyTorch 2.11 module API](https://docs.pytorch.org/docs/2.11/generated/torch.nn.Module.html).
4. Initial replay uses batch size 1, evaluation/inference mode, no gradients, and `use_cache=False`. Process one prefix at a time; request only the last vocabulary-logit row when the adapter supports it. This is deliberately easy to align and verify. Do not request all layers' full-sequence `output_hidden_states` from `generate`.
5. Once prefix replay is verified, optimize by capturing multiple causal positions from one teacher-forced pass over the base. Require numerical parity at selected positions against separate prefix replay, especially with Muse's sliding attention masks. Never silently assume chunked caching or a different attention backend is equivalent.

Define an adapter interface with `resolve_capture_sites`, `capture_prefixes`, and `capture_metadata`. Muse's exact module path is one adapter. Models outside validated adapters must show “activation capture not verified for this architecture”; a Hugging Face load succeeding is not enough. Generic hooks may exist, but module outputs and layer semantics differ.

### Memory and storage

Four BF16 vectors of width 6656 occupy **53,248 bytes per checkpoint**. For 256 checkpoints that is **13 MiB per trace**; six such traces need **78 MiB**, excluding metadata. FP32 export doubles those figures. These are arithmetic storage estimates, not measured GPU peaks.

By contrast, keeping all 52 layer outputs for 2,048 positions occupies about **1.32 GiB** in BF16 before other forward intermediates, logits, KV caches, and model weights. Full-sequence vocabulary logits add substantial memory with Muse's 202,048-token vocabulary. Selected hooks plus last-logit output avoid retaining these tensors; actual forward peak still needs measurement. A model fitting an A100 80GB for generation does not guarantee that every capture configuration fits.

Write CPU BF16 tensors as `safetensors` shards (already in the lockfiles); cast to FP32 on CPU for analysis. Use a JSON manifest mapping each tensor row to:

- Source run/pass, exact prefix token hash, checkpoint, absolute token index, problem and template-family IDs.
- Model and tokenizer revision, configuration hash, adapter and capture schema versions.
- Module path, zero-based block index, hook site semantics, layer attention type, tensor shape, stored and inference dtypes.
- Sampling settings, retained probability mass, target counts, matcher version, completion/ambiguity counts.
- Software versions, attention backend, cache/replay mode, collection time, capture runtime, measured peak allocated/reserved GPU memory.

Do not put large arrays in `result.json`. Add a versioned `activation_manifest` reference and keep old run schemas valid. Use data-only probe tensors and JSON rather than executable pickle payloads. Replaying an old run requires exact compatible model/tokenizer identity; refuse mismatches rather than attaching unrelated activations to a curve.

## Supervised outcome-probe MVP

Use one fixed category vocabulary across a dataset (for example A–D plus explicit unresolved status), rather than combining unrelated free-form answer lists. Use an objective, versioned answer extractor for the demonstration dataset and audit parsing. The user-selected mention matcher remains available for behavioral exploration, but its labels cannot be presented as truth or anticipation.

For each prefix `i`, train a regularized linear softmax map from one layer's frozen vector to its observed category proportions. Minimize cross-entropy against those proportions, with equal problem weighting so long traces do not dominate. Record sample counts; evaluate how uncertain targets affect the result. Train one readout per candidate layer, select layer and regularization on validation only, then freeze them.

Do not train on fitted/smoothed curves: those are model reconstructions and may spread information from later checkpoints backward. Use raw independent outcome counts. Keep cap hits, unparsed replies, and multiple matches distinguishable in stored targets; do not call them wrong answers. If filtering to completed, parsed replies, label the target as conditional on that filter and report excluded fractions.

### Data split and controls

- Assign problems and template families to train/validation/test **before generating continuations**. All checkpoints, option permutations, base traces, seeds, and continuations from related problems stay in one split.
- Use disjoint draws for training-label collection versus final reference evaluation where applicable. Never reuse the same outcomes both to train a probe and to score its claimed accuracy.
- Fit normalization/PCA (if later added) on training data only. Cache split hashes with the probe. No layer, checkpoint-window, threshold, or regularization selection using the test set.
- Compare against a train-set category prior; a position-only model; a prefix-text/answer-mention baseline; and a final-layer next-token feature baseline. These answer whether the probe adds anything beyond obvious answer text, progression through the response, or existing logits.
- Include shuffled-label controls at the independent-problem level, option-order counterbalancing, and a held-out template-family test. An apparent signal that survives only near explicit answer mentions is useful for parsing, but weak evidence for an earlier predictive state.
- Separately report prefixes before an explicit answer marker appears. Do not search each continuation for its final answer and use future-dependent truncation to decide which pre-branch activation to train on.

The current one-prompt, one-outcome run cannot pass these gates. The proposed six-trace offset benchmark is useful for debugging this pipeline, but six correlated problem groups would not support a strong generalization claim for 6,656-dimensional probes. Decide a larger dataset from a learning curve over independent problems and class coverage; there is no magic count of continuation draws that fixes too few problems.

### Evaluation and user flow

Report held-out log loss and Brier score, calibration, and per-category performance. Bootstrap uncertainty by independent problem/family, not continuation row. Compare probe predictions to newly sampled outcomes at held-out prefixes under the same branch selection and temperature. Show the number of independent test problems alongside all scores. For any “early warning” claim, hold out entire problems and measure how far before an independently defined behavioral change the fixed readout changes, with false alarms included.

User flow: open a saved trace → select a checkpoint/range → inspect capture support and estimated storage → collect or attach its activation shard → view layer/position vectors and export → attach a validated probe → see its evaluation card → optionally overlay predictions beside the behavioral curve. Clicking a disagreement shows the exact prefix, sample outcomes, completion quality, and model/capture metadata.

Use the labels **“sampled outcome frequency”** and **“probe-predicted outcome probability.”** Neither should be called a probability that a fork is real. Activation norm/cosine changes can be a supplementary exploratory heatmap, but token content and layer scale affect them; they are not learned semantic labels.

## What existing tools offer

| Tool | Useful existing capability | Decision for this MVP |
| --- | --- | --- |
| [NNsight](https://github.com/ndif-team/nnsight) | Access and intervention on existing PyTorch computation, including tracing | Strong future integration candidate. Native hooks suffice for four sites; do not add another loader or infer Muse support from generic library claims. |
| [TransformerLens](https://github.com/TransformerLensOrg/TransformerLens) | Activation caching and intervention interfaces; current bridge API preserves native HF weights by default | Consider for more standardized sites later. The current [registry](https://github.com/TransformerLensOrg/TransformerLens/blob/main/transformer_lens/tools/model_registry/data/supported_models.json) was fetched and contained no Muse-Glimmer match. That is lack of verified support, not proof that a generic bridge cannot work. |
| [Tuned Lens](https://github.com/AlignmentResearch/tuned-lens) | Existing intermediate prediction visualizations and trained translators | Reuse later if this is the desired question and a compatible translator is trained/verified. Do not label plain final-head projection as a trained tuned lens. |
| [pyvene](https://github.com/stanfordnlp/pyvene) | Serializable, composable internal interventions | Candidate for a later controlled patching workflow; not required for read-only capture. |
| [SAELens](https://github.com/decoderesearch/SAELens) | SAE training and analysis tooling | A pretrained SAE must match the exact model, layer, hook site and activation conventions. No compatible Muse artifact was verified in this review. Training an SAE is a different project. |

Dependency inspection: local locks specify Python 3.13, torch 2.11.0 (CPU or cu128), Transformers 5.16.1, accelerate 1.14.0, and safetensors 0.8.0. The native-hook MVP adds no mandatory external runtime dependency; a linear probe can use CPU PyTorch. NNsight's current [dependency metadata](https://raw.githubusercontent.com/ndif-team/nnsight/main/pyproject.toml) allows Python >=3.10 and torch >=2.4 with unpinned Transformers. Tuned Lens's [metadata](https://raw.githubusercontent.com/AlignmentResearch/tuned-lens/main/pyproject.toml) allows Python >=3.9 and Transformers >=4.38.1. Those bounds do **not** verify their actual compatibility with this pinned Python/Transformers/Muse combination. No dependency resolver or import/runtime check for those optional libraries was performed.

## Required acceptance checks before a GPU claim

1. Local tiny-model fixture: selected hook rows equal an independent full-hidden-state reference; hooks do not change logits; cleanup occurs on exceptions. Verify prompt/base indexing including `t=0`, variable prompt lengths, and padding.
2. Saved-input replay: hashes resolve to exactly the IDs in raw pass records, including special channel tokens. Capture does not re-render chat templates.
3. Data validation: reject mixed feature dimensions/sites/revisions, cross-split problem hashes, missing categories, and single-class training sets. Verify preprocessing fits training rows only.
4. GPU preflight on one short Muse prefix: compare baseline and instrumented logits, shapes, selected-state numerical tolerance, memory peak, and elapsed time. Any optimized batched/cached path needs its own parity check. Record tolerances and observed differences.
5. End-to-end saved activation export/reload without a GPU; probe predictions reproduce from frozen coefficients and metadata. Preserve existing sampling tests and results.

## What comes after, and what remains unknown

A validated readout can identify candidate locations for interventions. A later experiment could swap a specific residual vector between matched donor/recipient prefixes, then resample and compare to unchanged runs, sham swaps, and magnitude-matched random controls. Patching needs careful input alignment, metric choice, and cache handling; changing a decode activation without updating affected computation can test the wrong intervention. The interpretation is the effect of the specified perturbation, not the full natural mechanism. [How to use and interpret activation patching](https://arxiv.org/abs/2404.15255).

Hard unknowns are measured Muse capture overhead and memory, whether early features beat text/logit baselines, whether there is enough outcome diversity, whether a small linear map generalizes to new problems, and whether an optional framework preserves our exact generation numerics. Probes trained for one model/revision do not automatically transfer across models or context positions. Probe failure can reflect a changed representation or readout mismatch; probe success can reflect an unused correlation. Neither alone distinguishes “forgot the instruction” from “represented it but failed to comply.”

Feasibility: **high for capture/replay and a useful inspection/export UI; conditional on data quality for meaningful supervised readouts; unverified for causal or cross-model claims.** The product contribution would be making those distinctions and artifacts easy to inspect next to the fork curves. This report makes no novelty claim.
