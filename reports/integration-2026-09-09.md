# Loading, visualization and probe-design integration

Three agents completed separate workstreams. Loading and visualization were implemented; probe support remains a reviewed design, not a runtime feature.

- [Model loading implementation](model-loading-optimization.md)
- [Visualization implementation](fork-visualization-changes.md)
- [Probe proposal](probe-tools-proposal.md)

## Verification

The integrated checkout passed 76 Python tests and 10 JavaScript tests. The rebuilt CUDA container passed the same 76 Python and 10 JavaScript tests on a CPU-only host with network access disabled. Offline container startup with AUTO_LOAD_MODEL=0 reached idle with no attached model; the new graph module returned HTTP 200. An alternate CPU model profile resolved correctly without requesting weights. The temporary validation container was removed.

Local image: fork-microscope:runpod
Image ID: sha256:d73916afb988f1002c5ccd1901a25312f80c7e9cc32a7ace2635f6f578564e5b
Size: 7,696,992,824 bytes (uncompressed). Dependency layers were reused during the build.

Browser checks on the saved Muse pilot confirmed the default outcome is no, reconstruction is initially hidden, uncertainty bars are available, and no sampled change is claimed. A saved variable-outcome CPU run exposed its descriptive 0–1 interval (TV 0.400); the right-checkpoint button opened the correct five continuations. Backend now supplies explicit segmentation availability and band-type metadata; old records have conservative UI fallback behavior. The new JavaScript helper is on the server static allowlist, and CI discovers its tests.

No GPU was started for this work. Xet download tuning has not been benchmarked on a new RunPod host. No activation capture or probe training occurred. The new local image has not been pushed to GHCR; the previously published remote tag still identifies the earlier image. The local image was built from the working tree before the source commit; the commit records the tested implementation and these validation notes.
