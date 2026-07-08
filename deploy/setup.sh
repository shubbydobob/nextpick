#!/bin/bash
# EC2 Ubuntu 22.04 초기 설정 스크립트
# 실행: bash setup.sh
set -e

echo "=== [1/7] 시스템 업데이트 ==="
sudo apt-get update && sudo apt-get upgrade -y

echo "=== [2/7] Docker 설치 ==="
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker ubuntu
echo "Docker 설치 완료"

echo "=== [3/7] Python 3.12 설치 ==="
sudo apt-get install -y python3.12 python3.12-venv python3-pip git

echo "=== [4/7] Nginx 설치 ==="
sudo apt-get install -y nginx

echo "=== [5/7] 프로젝트 설정 ==="
REPO_DIR="/home/ubuntu/canslim"
cd $REPO_DIR

# Python 가상환경
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r etl/requirements.txt
echo "Python 환경 설정 완료"

echo "=== [6/7] Nginx 설정 ==="
sudo cp deploy/nginx.conf /etc/nginx/sites-available/canslim
sudo ln -sf /etc/nginx/sites-available/canslim /etc/nginx/sites-enabled/canslim
sudo rm -f /etc/nginx/sites-enabled/default
sudo mkdir -p /var/www/canslim
sudo nginx -t && sudo systemctl reload nginx

echo "=== [7/7] ETL crontab 등록 ==="
# 시간외 단일가가 20:00 KST에 끝나므로, 그 이후 확정 종가·상태로 채점하도록 20:05 실행.
(crontab -l 2>/dev/null; echo "5 20 * * 1-5 cd $REPO_DIR && $REPO_DIR/.venv/bin/python -m etl.kr_adapter.run_daily >> $REPO_DIR/etl_daily.log 2>&1") | crontab -
echo "crontab 등록 완료 (평일 20:05)"

echo ""
echo "======================================"
echo "초기 설정 완료. 이제 수동으로 해주세요:"
echo "  1. etl/config/db.yaml 생성"
echo "  2. etl/config/kis.yaml 생성"
echo "  3. .env 파일 생성 (DB_PASSWORD 설정)"
echo "  4. bash deploy/update.sh 실행"
echo "======================================"
