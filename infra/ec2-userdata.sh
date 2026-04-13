#!/usr/bin/env bash
set -euo pipefail

# Minimal EC2 bootstrap. Assumes Amazon Linux 2023 or Ubuntu 22.04+.
# Replace REPO_URL with your private git URL (or deploy via CodeDeploy / S3 tarball).

REPO_URL="${REPO_URL:-https://github.com/your-org/kuromi.git}"
APP_DIR="/opt/kuromi"

if command -v apt >/dev/null; then
  apt update -y && apt install -y python3.11 python3.11-venv git
elif command -v dnf >/dev/null; then
  dnf install -y python3.11 git
fi

id ubuntu >/dev/null 2>&1 || useradd -m -s /bin/bash ubuntu
mkdir -p "$APP_DIR" && chown ubuntu:ubuntu "$APP_DIR"
sudo -u ubuntu git clone "$REPO_URL" "$APP_DIR" || true

sudo -u ubuntu python3.11 -m venv "$APP_DIR/.venv"
sudo -u ubuntu "$APP_DIR/.venv/bin/pip" install -U pip
sudo -u ubuntu "$APP_DIR/.venv/bin/pip" install -e "$APP_DIR"

install -m 644 "$APP_DIR/infra/systemd/kuromi.service" /etc/systemd/system/kuromi.service
systemctl daemon-reload
systemctl enable --now kuromi
