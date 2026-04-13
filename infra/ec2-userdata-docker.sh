#!/usr/bin/env bash
# EC2 최초 기동 시 자동 실행. Docker + 디렉토리 구조 준비.
set -euo pipefail

apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release awscli

# Docker 공식 저장소
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | tee /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu

# 앱 디렉토리 구조
mkdir -p /opt/kuromi/{data,logs}
chown -R ubuntu:ubuntu /opt/kuromi

# 빈 .env 파일 (CI/CD가 채움)
touch /opt/kuromi/.env
chown ubuntu:ubuntu /opt/kuromi/.env

echo "kuromi userdata 완료"
