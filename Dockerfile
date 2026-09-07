FROM node:26-bookworm

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ca-certificates curl git gosu procps python3 tini build-essential zip unzip util-linux && rm -rf /var/lib/apt/lists/*
RUN npm install -g --allow-scripts=openclaw openclaw@2026.9.2 && npm install -g clawhub@latest

# Install gog (official OpenClaw Google Workspace CLI) as a small immutable binary.
ARG GOG_VERSION=0.39.1
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) gog_arch=amd64 ;; \
      arm64) gog_arch=arm64 ;; \
      *) echo "Unsupported architecture for gog: $arch" >&2; exit 1 ;; \
    esac; \
    tmpdir="$(mktemp -d)"; \
    curl -fsSL "https://github.com/openclaw/gogcli/releases/download/v${GOG_VERSION}/gogcli_${GOG_VERSION}_linux_${gog_arch}.tar.gz" \
      | tar -xz -C "$tmpdir"; \
    gog_bin="$(find "$tmpdir" -type f \( -name gog -o -name gogcli \) | head -n 1)"; \
    test -n "$gog_bin"; \
    install -m 0755 "$gog_bin" /usr/local/bin/gog; \
    rm -rf "$tmpdir"; \
    gog --version

# Install the official Codex plugin into a deterministic immutable path.
# Runtime only links this package into OpenClaw; nothing large is copied to /data.
RUN mkdir -p /opt/codex-runtime && \
    npm install --prefix /opt/codex-runtime @openclaw/codex@2026.9.2 && \
    test -f /opt/codex-runtime/node_modules/@openclaw/codex/package.json

WORKDIR /tmp
RUN git clone --depth 1 https://github.com/arjunkomath/openclaw-railway-template.git upstream
WORKDIR /app
RUN cp -a /tmp/upstream/. /app/ && rm -rf /tmp/upstream /app/.git

COPY patch-oauth.py /tmp/patch-oauth.py
RUN python3 /tmp/patch-oauth.py && rm /tmp/patch-oauth.py
COPY patch-single-gateway.py /tmp/patch-single-gateway.py
RUN python3 /tmp/patch-single-gateway.py && rm /tmp/patch-single-gateway.py
COPY patch-inference-test.py /tmp/patch-inference-test.py
RUN python3 /tmp/patch-inference-test.py && rm /tmp/patch-inference-test.py
COPY patch-google.py /tmp/patch-google.py
RUN python3 /tmp/patch-google.py && rm /tmp/patch-google.py
RUN npm install -g pnpm@11.24.0 && pnpm install --frozen-lockfile --prod

RUN useradd -m -s /bin/bash openclaw && chown -R openclaw:openclaw /app && mkdir -p /data && chown openclaw:openclaw /data && mkdir -p /home/linuxbrew/.linuxbrew && chown -R openclaw:openclaw /home/linuxbrew && chown -R openclaw:openclaw /opt/codex-runtime
USER openclaw
RUN NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

USER root
COPY jarvis-workspace/ /opt/jarvis-workspace/
COPY entrypoint-jarvis.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh && chown -R openclaw:openclaw /opt/jarvis-workspace

ENV PATH="/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:${PATH}"
ENV HOMEBREW_PREFIX="/home/linuxbrew/.linuxbrew"
ENV HOMEBREW_CELLAR="/home/linuxbrew/.linuxbrew/Cellar"
ENV HOMEBREW_REPOSITORY="/home/linuxbrew/.linuxbrew/Homebrew"
ENV GOG_HOME="/data/gog"
ENV GOG_KEYRING_BACKEND="file"
ENV PORT=8080
ENV OPENCLAW_ENTRY=/usr/local/lib/node_modules/openclaw/dist/entry.js
ENV OPENCLAW_SUPERVISOR_MODE=external
EXPOSE 8080

ENTRYPOINT ["tini", "--", "./entrypoint.sh"]
