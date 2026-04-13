#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Kuromi Trader — EC2 인스턴스 생성 스크립트 (one-shot)
# 사전 조건: AWS CLI 설치·인증 완료, 서울 리전(ap-northeast-2) 기본 설정
# 사용법:  KEY_PAIR_NAME=kitty-key bash infra/create-ec2.sh
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REGION="ap-northeast-2"
INSTANCE_NAME="kuromi-trader"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.small}"       # 2vCPU 2GB, 월 ~$15
KEY_PAIR_NAME="${KEY_PAIR_NAME:-kitty-key}"       # .pem 확장자 제외
DASHBOARD_PORT="8080"
ROLE_NAME="kuromi-ec2-role"
POLICY_NAME="kuromi-ec2-policy"
PROFILE_NAME="kuromi-ec2-profile"
REPO_NAME="kuromi"

echo "▶ [1/8] ECR 리포지토리 생성 (이미 있으면 무시)"
aws ecr create-repository --repository-name "$REPO_NAME" \
  --region "$REGION" --image-scanning-configuration scanOnPush=true \
  2>/dev/null || echo "  ECR 리포지토리 '$REPO_NAME' 이미 존재"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "  Account: $ACCOUNT_ID"

echo "▶ [2/8] IAM 역할 생성"
aws iam create-role --role-name "$ROLE_NAME" \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},
    "Action":"sts:AssumeRole"}]}' \
  --region "$REGION" 2>/dev/null || echo "  IAM 역할 이미 존재"

aws iam put-role-policy --role-name "$ROLE_NAME" \
  --policy-name "$POLICY_NAME" \
  --policy-document file://infra/iam-ec2-policy.json

aws iam create-instance-profile --instance-profile-name "$PROFILE_NAME" \
  2>/dev/null || echo "  인스턴스 프로파일 이미 존재"
aws iam add-role-to-instance-profile \
  --instance-profile-name "$PROFILE_NAME" --role-name "$ROLE_NAME" \
  2>/dev/null || echo "  역할 이미 연결됨"
echo "  잠시 대기 (IAM 전파)..."
sleep 15

echo "▶ [3/8] VPC 기본값 조회"
VPC_ID=$(aws ec2 describe-vpcs --region "$REGION" \
  --filters "Name=isDefault,Values=true" \
  --query "Vpcs[0].VpcId" --output text)
echo "  VPC: $VPC_ID"

echo "▶ [4/8] 보안 그룹 생성"
SG_ID=$(aws ec2 create-security-group \
  --group-name "kuromi-sg" \
  --description "Kuromi Trader security group" \
  --vpc-id "$VPC_ID" \
  --region "$REGION" \
  --query GroupId --output text 2>/dev/null) || \
SG_ID=$(aws ec2 describe-security-groups --region "$REGION" \
  --filters "Name=group-name,Values=kuromi-sg" \
  --query "SecurityGroups[0].GroupId" --output text)
echo "  SG: $SG_ID"

aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --region "$REGION" \
  --ip-permissions \
  "IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=0.0.0.0/0,Description=SSH}]" \
  "IpProtocol=tcp,FromPort=${DASHBOARD_PORT},ToPort=${DASHBOARD_PORT},IpRanges=[{CidrIp=0.0.0.0/0,Description=Dashboard}]" \
  2>/dev/null || echo "  인바운드 규칙 이미 존재"

echo "▶ [5/8] 최신 Ubuntu 22.04 AMI 조회"
AMI_ID=$(aws ec2 describe-images --region "$REGION" \
  --owners amazon \
  --filters \
    "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
    "Name=state,Values=available" \
  --query "sort_by(Images,&CreationDate)[-1].ImageId" \
  --output text)
echo "  AMI: $AMI_ID"

echo "▶ [6/8] EC2 인스턴스 생성"
INSTANCE_ID=$(aws ec2 run-instances \
  --region "$REGION" \
  --image-id "$AMI_ID" \
  --instance-type "$INSTANCE_TYPE" \
  --key-name "$KEY_PAIR_NAME" \
  --security-group-ids "$SG_ID" \
  --iam-instance-profile Name="$PROFILE_NAME" \
  --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=20,VolumeType=gp3}" \
  --user-data "$(cat infra/ec2-userdata-docker.sh)" \
  --tag-specifications \
    "ResourceType=instance,Tags=[{Key=Name,Value=${INSTANCE_NAME}}]" \
    "ResourceType=volume,Tags=[{Key=Name,Value=${INSTANCE_NAME}-root}]" \
  --query "Instances[0].InstanceId" --output text)
echo "  Instance ID: $INSTANCE_ID"

echo "▶ [7/8] 인스턴스 기동 대기..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

echo "▶ [8/8] Elastic IP 할당 및 연결"
EIP=$(aws ec2 allocate-address --domain vpc --region "$REGION" \
  --query AllocationId --output text)
aws ec2 associate-address --instance-id "$INSTANCE_ID" \
  --allocation-id "$EIP" --region "$REGION"

PUBLIC_IP=$(aws ec2 describe-addresses --region "$REGION" \
  --allocation-ids "$EIP" \
  --query "Addresses[0].PublicIp" --output text)

echo ""
echo "═══════════════════════════════════════════════"
echo "  kuromi-trader EC2 생성 완료"
echo "  Instance ID : $INSTANCE_ID"
echo "  Public IP   : $PUBLIC_IP"
echo "  Dashboard   : http://${PUBLIC_IP}:${DASHBOARD_PORT}"
echo "───────────────────────────────────────────────"
echo "  ⚙ GitHub Secrets에 다음 값을 등록하세요:"
echo "    EC2_HOST       = $PUBLIC_IP"
echo "    EC2_USER       = ubuntu"
echo "    AWS_ACCOUNT_ID = $ACCOUNT_ID"
echo "    SSH_PRIVATE_KEY= (~/kitty-key.pem 내용)"
echo "    AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY"
echo "    SECRETS_NAME   = kuromi/prod"
echo "───────────────────────────────────────────────"
echo "  ⏳ userdata 완료까지 약 3분 소요 후 배포 가능"
echo "═══════════════════════════════════════════════"
