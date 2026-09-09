# RunPod container

This image includes the CUDA Python environment, dashboard, and pinned Goodfire checkout. Muse weights download at startup; experiments do not run automatically. This is a private distribution because the upstream pinned repository does not supply a license (see THIRD-PARTY.md).

## Build

Start from a recursive Git clone, then run:

```bash
docker build -t fork-microscope:runpod .
```

The Git metadata is required by the revision checks. Build from a clean checkout without credentials in Git configuration. Model weights, experiment results and the local Python environment are excluded from the build context.

The manually triggered **Build private RunPod image** GitHub Actions workflow publishes to `ghcr.io/ipolluxx/fork-microscope:<full-commit-sha>`. Use the immutable commit tag shown by that workflow. The image/package must remain private; do not change its visibility without resolving upstream licensing.

## RunPod template settings

- Container image: the published GHCR image and commit tag.
- Registry credentials: your GitHub username and a credential with permission to read that private package. Enter this in RunPod's registry credential settings, not in the image or Git repository.
- Compute: one NVIDIA A100 80GB, public IP, on-demand.
- Container disk: 200–250GB. No persistent volume is required.
- Expose TCP port: `22`.
- HTTP ports: none required; the dashboard is accessed through SSH.
- Container start command: leave blank (use the image entrypoint).
- Environment: `SSH_PUBLIC_KEY` = your public key, `AUTO_LOAD_MUSE` = `1` (default).
- Set `AUTO_LOAD_MUSE=0` to start the dashboard without downloading/loading a model.

The image accepts RunPod's `PUBLIC_KEY` variable too, with `SSH_PUBLIC_KEY` taking precedence. Host keys are generated when the container starts. Password SSH is disabled.

## Connect

Take the IP and exposed SSH port from the Pod's Connect panel:

```bash
ssh -N -L 8767:127.0.0.1:8767 -p POD_SSH_PORT -i ~/.ssh/id_ed25519 root@POD_IP
```

Open http://127.0.0.1:8767/live.html. Both the local and remote dashboard ports must be 8767. If preflight fails, SSH remains available and the error is saved to `/workspace/doctor.log`; no model is loaded. Startup output is in RunPod's container logs; the dashboard reports model-loading status. Do not click Load again while automatic loading is in progress.

## Download results before stopping

Run on your computer:

```bash
mkdir -p runpod-results
scp -r -P POD_SSH_PORT -i ~/.ssh/id_ed25519 root@POD_IP:/workspace/live-runs ./runpod-results/
```

The application lives at `/opt/fork-microscope`, model cache at `/workspace/huggingface`, and results at `/workspace/live-runs`. Without a persistent volume, all three are disposable when the Pod stops. The image is downloaded again if the next host has no cached copy. No startup-time or throughput improvement is claimed until measured on RunPod.

## Earlier validation (2026-09-08)

The CUDA image built locally. With `AUTO_LOAD_MUSE=0`, injected public-key SSH authentication, automatic dashboard startup, its status endpoint, and the results directory link passed on a CPU-only host. The existing 34 Python and 3 JavaScript tests passed. Container-based GPU inference and RunPod deployment remain untested; the earlier Muse GPU test used the non-container installation. The publishing workflow is present but has not been dispatched.


## Updated build (2026-09-09)

Source: `c08c79307d3383e473bb2eca6837684b32c8021f`. Local image: `fork-microscope:runpod`, image ID `682eb64704454383d1b9e61d84fba4d8ce3ee61067d8b00fab114f9f65e4f822`.

This update includes custom prompt/answer tracking, the continuation library, Node.js 22 for verification, and `configs/muse-anticipation.json` with Isaiah's exact question. It passed 62 Python and five JavaScript tests inside the rebuilt container. Dashboard startup with Muse auto-loading disabled and the `/workspace/live-runs` storage link were checked locally. GPU inference has not been tested in this container.

The question profile is a separate experiment configuration; startup does not execute it. Generate and inspect the response first, then choose checkpoint locations appropriate to its actual length. See the main README's Muse anticipation section.

Published private RunPod image:

```text
ghcr.io/ipolluxx/fork-microscope:035d4da70050aa2c42c87ce173f7e3fd25a997d0
```

Registry digest: `sha256:8705a302eb48ab569ce1dc07435131f2390d7bff42cf1b861a16481837e1d634`. The published source differs from the tested local source only by the hosted-runner disk-cleanup workflow fix. Publication and explicit private-visibility verification passed: https://github.com/iPolluxx/fork-microscope/actions/runs/34374004796

In RunPod, use the image tag above with a private-registry credential for `ghcr.io` (GitHub username `iPolluxx`, token with `read:packages`). The existing local GitHub CLI credential lacks that scope; it was not changed. Visibility was verified using the publishing workflow's package-scoped credential. An authenticated remote pull and RunPod GPU launch remain untested.

The first cloud publication attempt ran out of runner disk while installing CUDA wheels. The workflow now removes unrelated preinstalled SDKs from its disposable GitHub runner before building. No files on the user's computer are removed by that step.
