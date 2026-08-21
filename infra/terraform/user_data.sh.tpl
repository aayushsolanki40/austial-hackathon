#!/bin/bash
# Bootstraps the backend EC2 instance: installs Docker, logs into ECR, and
# runs the Austial backend stack -- API, Redis (Celery broker/result
# backend), and a Celery worker -- as three sibling containers on a
# user-defined Docker network (so they can resolve each other by container
# name, e.g. REDIS_URL=redis://redis:6379/0), plus a one-off Alembic
# migration run before the API container starts.
#
# The image is pulled in a retry loop because this instance can boot before
# the first `docker push` to ECR has happened (Terraform creates the empty
# repo, then the image is built/pushed as a separate step) -- this avoids
# having to manually re-trigger user-data / reboot the instance afterwards.
set -x
exec > >(tee /var/log/austial-user-data.log) 2>&1

dnf install -y docker
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

IMAGE="${ecr_repo_url}:${image_tag}"
DATABASE_URL="postgresql+asyncpg://${db_username}:${db_password}@${db_endpoint}/${db_name}"
REDIS_URL="redis://redis:6379/0"

aws ecr get-login-password --region "${aws_region}" | docker login --username AWS --password-stdin "${ecr_registry}"

for i in $(seq 1 80); do
  if docker pull "$IMAGE"; then
    break
  fi
  echo "image not available yet, retrying in 15s ($i/80)"
  sleep 15
done

# User-defined bridge network -- unlike the default bridge, this gives containers Docker's
# embedded DNS so "redis" (the container name below) resolves for the app/worker containers.
docker network create austial-net || true

docker rm -f austial-redis austial-backend austial-worker austial-migrate 2>/dev/null || true

docker run -d \
  --name austial-redis \
  --restart unless-stopped \
  --network austial-net \
  --network-alias redis \
  redis:7-alpine

# One-off migration run -- `alembic upgrade head` is idempotent (no-ops if already at head), so
# running it on every boot (fresh instance *and* any future instance replacement) is safe and
# keeps the schema in sync without a separate manual SSM step. See backend/alembic/README.md.
for i in $(seq 1 10); do
  if docker run --rm \
    --network austial-net \
    -e DATABASE_URL="$DATABASE_URL" \
    "$IMAGE" python -m alembic upgrade head; then
    break
  fi
  echo "migration failed (RDS likely still starting), retrying in 15s ($i/10)"
  sleep 15
done

docker run -d \
  --name austial-backend \
  --restart unless-stopped \
  --network austial-net \
  -p ${app_port}:${app_port} \
  -e DATABASE_URL="$DATABASE_URL" \
  -e API_KEY="${api_key}" \
  -e PORT=${app_port} \
  -e JWT_SECRET="${jwt_secret}" \
  -e JWT_ACCESS_TOKEN_TTL_MINUTES=${jwt_access_token_ttl_minutes} \
  -e JWT_REFRESH_TOKEN_TTL_DAYS=${jwt_refresh_token_ttl_days} \
  -e REDIS_URL="$REDIS_URL" \
  -e DOCUMENTS_S3_BUCKET="${documents_s3_bucket}" \
  -e AWS_REGION="${aws_region}" \
  "$IMAGE"

docker run -d \
  --name austial-worker \
  --restart unless-stopped \
  --network austial-net \
  -e DATABASE_URL="$DATABASE_URL" \
  -e JWT_SECRET="${jwt_secret}" \
  -e REDIS_URL="$REDIS_URL" \
  -e DOCUMENTS_S3_BUCKET="${documents_s3_bucket}" \
  -e AWS_REGION="${aws_region}" \
  "$IMAGE" celery -A src.jobs.celery_app worker --loglevel=info

echo "user-data complete"
