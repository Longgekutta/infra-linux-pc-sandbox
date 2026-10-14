# Linux PC Sandbox - High-Density Stealth Container
# Base: Debian 12 Slim with Chromium, Xvfb, and Authentic Desktop Font Packs

FROM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    DISPLAY_WIDTH=1920 \
    DISPLAY_HEIGHT=1080 \
    DISPLAY_DEPTH=24 \
    CDP_PORT=9222

# 1. Install Chromium, Xvfb, Mesa utilities, tini init process, and diverse desktop fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    chromium \
    xvfb \
    x11-utils \
    mesa-utils \
    fonts-liberation \
    fonts-noto-color-emoji \
    fonts-dejavu-core \
    fonts-noto-cjk \
    ca-certificates \
    procps \
    curl \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 2. Workspace and directories
WORKDIR /app
RUN mkdir -p /data/profile /var/log/sandbox

# 3. Copy application files
COPY . /app/

# 4. Entrypoint script
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 9222

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
CMD ["python3", "-m", "cli", "worker", "--port", "9222"]

