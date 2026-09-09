FROM python:3.13-slim-bookworm
ENV DEBIAN_FRONTEND=noninteractive \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH=/opt/fork-microscope/.venv/bin:$PATH \
    HF_HOME=/workspace/huggingface \
    OTRECON_FORCE_RUPTURES=1 \
    PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends git openssh-server ca-certificates tini curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.11.2
WORKDIR /opt/fork-microscope
COPY requirements/ requirements/
RUN uv venv --python /usr/local/bin/python .venv \
    && uv pip sync --python .venv/bin/python --index https://download.pytorch.org/whl/cu128 \
       --index-strategy unsafe-best-match requirements/cuda.lock \
    && uv cache clean
COPY . .
RUN uv pip install --python .venv/bin/python --no-deps ./vendor/forking-fast/otrecon ./vendor/forking-fast/forking_paths \
    && uv pip install --python .venv/bin/python --no-deps --editable . \
    && uv cache clean \
    && chmod +x docker/start.sh \
    && rm -f /etc/ssh/ssh_host_* \
    && mkdir -p /run/sshd \
    && printf '\nPasswordAuthentication no\nPermitRootLogin prohibit-password\n' >> /etc/ssh/sshd_config
EXPOSE 22
ENTRYPOINT ["/usr/bin/tini", "--", "/opt/fork-microscope/docker/start.sh"]
