#!/bin/bash
# Bootstraps the backend EC2 instance: installs Docker, logs into ECR, and
# runs the Austial backend container against the RDS instance.
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

aws ecr get-login-password --region "${aws_region}" | docker login --username AWS --password-stdin "${ecr_registry}"

for i in $(seq 1 80); do
  if docker pull "$IMAGE"; then
    break
  fi
  echo "image not available yet, retrying in 15s ($i/80)"
  sleep 15
done

docker run -d \
  --name austial-backend \
  --restart unless-stopped \
  -p ${app_port}:${app_port} \
  -e DATABASE_URL="postgresql+asyncpg://${db_username}:${db_password}@${db_endpoint}/${db_name}" \
  -e API_KEY="${api_key}" \
  -e PORT=${app_port} \
  "$IMAGE"

echo "user-data complete"
