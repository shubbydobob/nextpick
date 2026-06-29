#!/bin/bash
# 배포 업데이트 스크립트 (git pull 후 재배포)
# 실행: bash deploy/update.sh
set -e

REPO_DIR="/home/ubuntu/canslim"
cd $REPO_DIR

echo "=== [1/4] 코드 업데이트 ==="
git pull

echo "=== [2/4] Docker 서비스 재시작 ==="
docker compose -f docker-compose.prod.yml up -d --build
echo "Spring Boot + PostgreSQL 기동 완료"

echo "=== [3/4] React 빌드 ==="
cd frontend
npm ci --silent
npm run build
cd ..
sudo cp -r frontend/dist/. /var/www/canslim/
echo "React 빌드 완료"

echo "=== [4/4] Nginx 리로드 ==="
sudo systemctl reload nginx

echo ""
echo "배포 완료!"
echo "  API:  http://$(curl -s ifconfig.me):80/api/screener?market=KR"
echo "  Web:  http://$(curl -s ifconfig.me)"
