#!/bin/bash

# Austial Deployment Script
# Builds and deploys frontend + backend to AWS

set -e  # Exit on error

echo "🚀 Starting Austial Deployment..."
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed${NC}"
        exit 1
    fi
}

echo "Checking prerequisites..."
check_command npm
check_command docker
check_command terraform
check_command aws

# Get AWS profile
AWS_PROFILE="${AWS_PROFILE:-aayush-gift}"
echo -e "${YELLOW}Using AWS profile: $AWS_PROFILE${NC}"

# Verify AWS credentials
echo "Verifying AWS credentials..."
aws sts get-caller-identity --profile $AWS_PROFILE > /dev/null || {
    echo -e "${RED}❌ AWS credentials invalid for profile $AWS_PROFILE${NC}"
    exit 1
}

echo -e "${GREEN}✅ Prerequisites OK${NC}"
echo ""

# Step 1: Build Frontend
echo "📦 Step 1: Building Frontend..."
cd frontend
npm install
npm run build

if [ ! -d "dist/austial-app/browser" ]; then
    echo -e "${RED}❌ Frontend build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Frontend built successfully${NC}"
echo ""

# Step 2: Deploy Frontend to S3
echo "☁️  Step 2: Deploying Frontend to S3..."
cd ../infra/terraform

terraform init -input=false

# Upload frontend
echo "Uploading to S3..."
aws s3 sync ../../frontend/dist/austial-app/browser/ s3://austial-frontend-bucket/ \
    --profile $AWS_PROFILE \
    --delete \
    --cache-control "max-age=3600"

echo -e "${GREEN}✅ Frontend deployed to S3${NC}"
echo ""

# Step 3: Build Backend Docker Image
echo "🐳 Step 3: Building Backend Docker Image..."
cd ../../backend

docker build -t austial-backend:latest .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Backend Docker build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backend Docker image built${NC}"
echo ""

# Step 4: Push to ECR
echo "📤 Step 4: Pushing to ECR..."

# Login to ECR
aws ecr get-login-password --region us-east-1 --profile $AWS_PROFILE | \
    docker login --username AWS --password-stdin 459141725579.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag austial-backend:latest 459141725579.dkr.ecr.us-east-1.amazonaws.com/austial-backend:latest

# Push to ECR
docker push 459141725579.dkr.ecr.us-east-1.amazonaws.com/austial-backend:latest

echo -e "${GREEN}✅ Backend pushed to ECR${NC}"
echo ""

# Step 5: Deploy to EC2
echo "🖥️  Step 5: Deploying to EC2..."

# Check if we should SSH deploy or just provide instructions
if [ -f ~/.ssh/austial-ec2.pem ]; then
    echo "SSH key found, deploying to EC2..."

    # SSH and deploy
    ssh -i ~/.ssh/austial-ec2.pem ec2-user@52.6.51.39 << 'EOF'
        # Login to ECR
        aws ecr get-login-password --region us-east-1 | \
            docker login --username AWS --password-stdin 459141725579.dkr.ecr.us-east-1.amazonaws.com

        # Pull latest image
        docker pull 459141725579.dkr.ecr.us-east-1.amazonaws.com/austial-backend:latest

        # Stop old container
        docker stop austial-backend || true
        docker rm austial-backend || true

        # Run new container
        docker run -d \
            --name austial-backend \
            -p 8000:8000 \
            --env-file /home/ec2-user/.env \
            --restart unless-stopped \
            459141725579.dkr.ecr.us-east-1.amazonaws.com/austial-backend:latest

        # Run migrations
        sleep 5
        docker exec -it austial-backend uv run alembic upgrade head

        echo "Backend deployed successfully"
EOF

    echo -e "${GREEN}✅ Backend deployed to EC2${NC}"
else
    echo -e "${YELLOW}⚠️  No SSH key found at ~/.ssh/austial-ec2.pem${NC}"
    echo "Manual deployment required. SSH into EC2 and run:"
    echo ""
    echo "  ssh -i ~/.ssh/your-key.pem ec2-user@52.6.51.39"
    echo "  docker pull 459141725579.dkr.ecr.us-east-1.amazonaws.com/austial-backend:latest"
    echo "  docker stop austial-backend && docker rm austial-backend"
    echo "  docker run -d --name austial-backend -p 8000:8000 --env-file ~/.env --restart unless-stopped 459141725579.dkr.ecr.us-east-1.amazonaws.com/austial-backend:latest"
    echo "  docker exec -it austial-backend uv run alembic upgrade head"
    echo ""
fi

echo ""

# Step 6: Verify Deployment
echo "✅ Step 6: Verifying Deployment..."

# Check frontend
echo "Checking frontend..."
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://austial-frontend-bucket.s3-website-us-east-1.amazonaws.com/home)
if [ $FRONTEND_STATUS -eq 200 ]; then
    echo -e "${GREEN}✅ Frontend: OK (HTTP $FRONTEND_STATUS)${NC}"
else
    echo -e "${RED}❌ Frontend: FAILED (HTTP $FRONTEND_STATUS)${NC}"
fi

# Check backend
echo "Checking backend..."
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://52.6.51.39:8000/health)
if [ $BACKEND_STATUS -eq 200 ]; then
    echo -e "${GREEN}✅ Backend: OK (HTTP $BACKEND_STATUS)${NC}"
else
    echo -e "${RED}❌ Backend: FAILED (HTTP $BACKEND_STATUS)${NC}"
fi

echo ""
echo "=================================="
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo ""
echo "Frontend URL: http://austial-frontend-bucket.s3-website-us-east-1.amazonaws.com"
echo "Backend API: http://52.6.51.39:8000"
echo "API Docs: http://52.6.51.39:8000/docs"
echo ""
echo "Test Credentials:"
echo "  Investor: investor@test.com / password123"
echo "  Admin: admin@test.com / password123"
echo ""
