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

Open http://127.0.0.1:8767/live.html. Both the local and remote dashboard ports must be 8767. Startup output is in RunPod's container logs; the dashboard reports model-loading status. Do not click Load again while automatic loading is in progress.

## Download results before stopping

Run on your computer:

```bash
mkdir -p runpod-results
scp -r -P POD_SSH_PORT -i ~/.ssh/id_ed25519 root@POD_IP:/workspace/live-runs ./runpod-results/
```

The application lives at `/opt/fork-microscope`, model cache at `/workspace/huggingface`, and results at `/workspace/live-runs`. Without a persistent volume, all three are disposable when the Pod stops. The image is downloaded again if the next host has no cached copy. No startup-time or throughput improvement is claimed until measured on RunPod.

## Validation (2026-09-08)

The CUDA image built locally. With `AUTO_LOAD_MUSE=0`, injected public-key SSH authentication, automatic dashboard startup, its status endpoint, and the results directory link passed on a CPU-only host. The existing 34 Python and 3 JavaScript tests passed. Container-based GPU inference and RunPod deployment remain untested; the earlier Muse GPU test used the non-container installation. The publishing workflow is present but has not been dispatched.
