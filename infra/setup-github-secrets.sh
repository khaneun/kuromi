#!/usr/bin/env bash
# GitHub CLI(gh)로 GitHub Secrets를 일괄 등록합니다.
# 사전 조건: gh auth login 완료, create-ec2.sh 실행 후 EC2_HOST 확인
# 사용법: EC2_HOST=<IP> REPO=<owner/kuromi> bash infra/setup-github-secrets.sh
set -euo pipefail

REPO="${REPO:?REPO 환경변수 필요 (예: khaneun/kuromi)}"
KEY_PATH="${KEY_PATH:-~/kitty-key.pem}"
EC2_HOST="${EC2_HOST:?EC2_HOST 환경변수 필요}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID 필요}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY 필요}"

echo "▶ GitHub Secrets 등록: $REPO"

gh secret set SSH_PRIVATE_KEY       --repo "$REPO" --body "$(cat $KEY_PATH)"
gh secret set EC2_HOST              --repo "$REPO" --body "$EC2_HOST"
gh secret set EC2_USER              --repo "$REPO" --body "ubuntu"
gh secret set AWS_ACCOUNT_ID        --repo "$REPO" --body "$AWS_ACCOUNT_ID"
gh secret set AWS_ACCESS_KEY_ID     --repo "$REPO" --body "$AWS_ACCESS_KEY_ID"
gh secret set AWS_SECRET_ACCESS_KEY --repo "$REPO" --body "$AWS_SECRET_ACCESS_KEY"
gh secret set SECRETS_NAME          --repo "$REPO" --body "kuromi/prod"

echo ""
echo "✅ Secrets 등록 완료:"
gh secret list --repo "$REPO"
