#!/usr/bin/env bash
set -euo pipefail
cd /opt/fork-microscope
mkdir -p /workspace/live-runs /root/.ssh /run/sshd
chmod 700 /root/.ssh
# Official RunPod templates use PUBLIC_KEY; also accept the per-Pod override.
key="${SSH_PUBLIC_KEY:-${PUBLIC_KEY:-}}"
if [[ -n "$key" ]]; then
    printf '%s\n' "$key" >> /root/.ssh/authorized_keys
    sort -u /root/.ssh/authorized_keys -o /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
fi
ssh-keygen -A
/usr/sbin/sshd
if [[ ! -e live-runs ]]; then ln -s /workspace/live-runs live-runs; fi
# Fail on package / CUDA configuration errors before presenting a ready service.
fork-microscope doctor
if [[ "${AUTO_LOAD_MUSE:-1}" == 1 ]]; then
    python docker/autoload.py &
fi
exec fork-microscope serve --port 8767
