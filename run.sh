#!/bin/bash

echo "Deploying to AWS server on port 80..."

# 기존 컨테이너 중지 및 제거
docker stop fycus_backend 2>/dev/null || true
docker rm fycus_backend 2>/dev/null || true

# 기존 이미지 제거
docker rmi fycus_backend 2>/dev/null || true

# 새 이미지 빌드 (프로덕션용)
echo "Building Docker image..."
docker build -f Dockerfile -t fycus_backend .

# 컨테이너 실행 (포트 80)
echo "Starting container on port 80..."
docker run -d \
  --name fycus_backend \
  -p 80:8000 \
  -e DEBUG=False \
  -e DJANGO_SETTINGS_MODULE=Aim_Goza_Backend.settings \
  --restart unless-stopped \
  fycus_backend

echo "Deployment completed!"
echo "Container status:"
docker ps

echo "Logs:"
docker logs fycus_backend

echo "Testing connection..."
sleep 5
curl -I http://localhost:80
