#!/bin/bash
# 로컬 DB → 덤프 파일 생성 후 EC2로 전송
# 실행: bash deploy/db-dump.sh <EC2_IP> <EC2_PEM_KEY>
# 예시: bash deploy/db-dump.sh 13.125.x.x ~/.ssh/canslim-key.pem
set -e

EC2_IP=$1
PEM_KEY=$2

if [ -z "$EC2_IP" ] || [ -z "$PEM_KEY" ]; then
  echo "사용법: bash deploy/db-dump.sh <EC2_IP> <PEM_KEY_PATH>"
  exit 1
fi

DUMP_FILE="canslim_$(date +%Y%m%d).dump"

echo "=== [1/3] DB 덤프 생성 ==="
docker exec canslim-postgres pg_dump \
  -U canslim_user canslim \
  --no-owner --no-acl -F c \
  -f /tmp/$DUMP_FILE
docker cp canslim-postgres:/tmp/$DUMP_FILE ./$DUMP_FILE
echo "덤프 완료: $DUMP_FILE ($(du -sh $DUMP_FILE | cut -f1))"

echo "=== [2/3] EC2로 전송 ==="
scp -i $PEM_KEY $DUMP_FILE ubuntu@$EC2_IP:~/
echo "전송 완료"

echo "=== [3/3] EC2에서 복원 ==="
ssh -i $PEM_KEY ubuntu@$EC2_IP << REMOTE
  docker cp ~/$DUMP_FILE canslim-postgres:/tmp/
  docker exec canslim-postgres pg_restore \
    -U canslim_user -d canslim \
    --no-owner -F c /tmp/$DUMP_FILE
  echo "복원 완료"
REMOTE

rm -f ./$DUMP_FILE
echo ""
echo "DB 마이그레이션 완료!"
