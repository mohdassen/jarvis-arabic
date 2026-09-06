FROM node:26-bookworm

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ca-certificates curl git gosu procps python3 tini build-essential zip unzip util-linux && rm -rf /var/lib/apt/lists/*
RUN npm install -g --allow-scripts=openclaw openclaw@2026.9.2 && npm install -g clawhub@latest

# Pre-install the official Codex plugin during image build so Railway runtime
# does not have to run a memory-heavy npm install on the small service instance.
RUN mkdir -p /opt/openclaw-plugin-seed && \
    OPENCLAW_STATE_DIR=/opt/openclaw-plugin-seed \
    openclaw plugins install npm:@openclaw/codex@2026.9.2

WORKDIR /tmp
RUN git clone --depth 1 https://github.com/arjunkomath/openclaw-railway-template.git upstream
WORKDIR /app
RUN cp -a /tmp/upstream/. /app/ && rm -rf /tmp/upstream /app/.git

COPY patch-oauth.py /tmp/patch-oauth.py
RUN python3 /tmp/patch-oauth.py && rm /tmp/patch-oauth.py
COPY patch-single-gateway.py /tmp/patch-single-gateway.py
RUN python3 /tmp/patch-single-gateway.py && rm /tmp/patch-single-gateway.py
RUN npm install -g pnpm@11.24.0 && pnpm install --frozen-lockfile --prod

RUN useradd -m -s /bin/bash openclaw && chown -R openclaw:openclaw /app && mkdir -p /data && chown openclaw:openclaw /data && mkdir -p /home/linuxbrew/.linuxbrew && chown -R openclaw:openclaw /home/linuxbrew && chown -R openclaw:openclaw /opt/openclaw-plugin-seed
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
ENV PORT=8080
ENV OPENCLAW_ENTRY=/usr/local/lib/node_modules/openclaw/dist/entry.js
ENV OPENCLAW_SUPERVISOR_MODE=external
EXPOSE 8080

ENTRYPOINT ["tini", "--", "./entrypoint.sh"]
