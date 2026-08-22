# Austial Landing Page & App Deployment Guide

This guide covers deploying the Austial platform (backend API + Angular frontend with new landing page) to AWS.

---

## WHAT'S NEW

### Landing Page Added
- **Location:** `frontend/src/app/features/landing/landing.component.ts`
- **Route:** `/home` (public, no auth required)
- **Features:**
  - Hero section with key stats
  - Embedded pitch video placeholder
  - Problem/Solution sections
  - Live demo links
  - Test credentials
  - Full Young Builders Program pitch content

### Route Changes
- **Public routes:** `/`, `/home`, `/login`, `/register`
- **Authenticated routes:** `/app/*` (marketplace, portfolio, wallet)
- **Admin routes:** `/admin/*` (unchanged)
- **Default:** Redirects to `/home` (landing page)

---

## QUICK START (Local Development)

### Backend

```bash
cd backend
uv sync
cp .env.example .env
# Edit .env with your DATABASE_URL, API_KEY, etc.

# Run migrations
uv run alembic upgrade head

# Start server
uv run austial serve
# API available at http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install

# Start dev server
npm start
# App available at http://localhost:4200
# Landing page at http://localhost:4200/home
```

---

## PRODUCTION DEPLOYMENT (AWS)

### Prerequisites

1. **AWS CLI configured with `aayush-gift` profile**
   ```bash
   export AWS_ACCESS_KEY_ID=your_key_here
   export AWS_SECRET_ACCESS_KEY=your_secret_here
   export AWS_DEFAULT_REGION=us-east-1
   ```

2. **Terraform installed** (>= 1.5.0)

3. **Docker installed** (for building images)

### Step 1: Build Frontend

```bash
cd frontend
npm install
npm run build
# Outputs to frontend/dist/austial-app/browser/
```

### Step 2: Upload Frontend to S3

```bash
cd infra/terraform

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Apply (creates S3 bucket + uploads frontend)
terraform apply
```

**Frontend URL:** http://austial-frontend-bucket.s3-website-us-east-1.amazonaws.com

### Step 3: Build & Deploy Backend Docker Image

```bash
cd backend

# Build Docker image
docker build -t austial-backend:latest .

# Tag for ECR
docker tag austial-backend:latest 459141725579.dkr.ecr.us-east-1.amazonaws.com/austial-backend:latest

# Login to ECR
aws ecr get-login-password --region us-east-1 --profile aayush-gift | \
  docker login --username AWS --password-stdin 459141725579.dkr.ecr.us-east-1.amazonaws.com

# Push to ECR
docker push 459141725579.dkr.ecr.us-east-1.amazonaws.com/austial-backend:latest
```

### Step 4: Deploy Backend to EC2

```bash
cd infra/terraform

# SSH into EC2 instance
ssh -i ~/.ssh/your-key.pem ec2-user@52.6.51.39

# Pull latest image
docker pull 459141725579.dkr.ecr.us-east-1.amazonaws.com/austial-backend:latest

# Stop old container
docker stop austial-backend || true
docker rm austial-backend || true

# Run new container
docker run -d \
  --name austial-backend \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@rds-endpoint:5432/austial" \
  -e API_KEY="your-api-key-here" \
  -e REDIS_URL="redis://localhost:6379" \
  -e DOCUMENTS_S3_BUCKET="austial-documents" \
  -e AWS_REGION="us-east-1" \
  --restart unless-stopped \
  459141725579.dkr.ecr.us-east-1.amazonaws.com/austial-backend:latest

# Check logs
docker logs -f austial-backend
```

### Step 5: Run Database Migrations

```bash
# SSH into EC2
ssh -i ~/.ssh/your-key.pem ec2-user@52.6.51.39

# Run migrations inside container
docker exec -it austial-backend uv run alembic upgrade head
```

---

## AUTOMATED DEPLOYMENT (Recommended)

Use the `sync-aws-infra` skill for automated deployment:

```bash
# From the workspace root
claude code

# In Claude Code session:
> use the sync-aws-infra skill to deploy the latest changes
```

This will:
1. Check for Terraform drift
2. Build frontend & backend
3. Upload to S3 / push to ECR
4. Update EC2 container
5. Run migrations
6. Test live endpoints

---

## VERIFICATION

### Check Backend Health

```bash
curl http://52.6.51.39:8000/health
# Should return: {"status":"ok","checks":{"database":"up","memory_heap":"healthy"}}
```

### Check Frontend

```bash
# Landing page
curl -I http://austial-frontend-bucket.s3-website-us-east-1.amazonaws.com/home
# Should return: 200 OK

# Open in browser
open http://austial-frontend-bucket.s3-website-us-east-1.amazonaws.com/home
```

### Test API Docs

Open: http://52.6.51.39:8000/docs

---

## VIDEO SETUP

### Placeholder Video Link

The landing page currently has a **placeholder YouTube video** (`dQw4w9WgXcQ`).

### Replace with Your Pitch Video

1. **Record your pitch video** (5-10 minutes recommended):
   - Problem statement (2 min)
   - Solution demo (3-5 min)
   - Validation & team (2 min)
   - Call to action (1 min)

2. **Upload to YouTube:**
   - Title: "Austial - RWA Tokenization Platform for GIFT City"
   - Description: Include pitch deck link, live demo URL, contact info
   - Tags: IFSCA, GIFT City, RWA, tokenization, fintech, Young Builders

3. **Get embed code:**
   - Copy the video ID from YouTube URL: `https://youtube.com/watch?v=VIDEO_ID_HERE`
   
4. **Update landing page:**
   ```typescript
   // In frontend/src/app/features/landing/landing.component.ts
   // Find line:
   src="https://www.youtube.com/embed/dQw4w9WgXcQ"
   
   // Replace with:
   src="https://www.youtube.com/embed/YOUR_VIDEO_ID_HERE"
   ```

5. **Rebuild & redeploy:**
   ```bash
   cd frontend
   npm run build
   cd ../infra/terraform
   terraform apply
   ```

---

## VIDEO SCRIPT (Template)

### Opening (30 sec)
"Hi, I'm [Name] from Austial. We're building a GIFT City-based platform that makes Indian real estate, commodities, and infrastructure accessible to NRI and foreign investors through fractional tokenization. Here's the problem we're solving..."

### Problem (2 min)
- Show stats: $10-50B tokenizable assets, 5-10 day SWIFT settlement
- Explain investor pain (high minimums, no liquidity)
- Explain issuer pain (3-4% placement fees)
- Show GIFT City infrastructure exists but lacks operating platform

### Solution Demo (3-5 min)
**Screen recording walkthrough:**
1. Landing page overview
2. Register → KYC submission (show OCR working)
3. Browse marketplace → view asset prospectus
4. Subscribe to tokenized real estate offering
5. View holding in portfolio
6. Request redemption
7. Admin dashboard (KYC approval, AML monitoring)

### Technology & Validation (2 min)
- Architecture slide: 24 entities, 15 modules, 100+ tests
- Customer interviews: 3 developers, 2 fund managers, 2 NRI investors
- Competitive positioning: Austial vs. Zoniqx vs. global DLT
- Live deployment metrics

### Regulatory Pathway (1 min)
- IFSCA Sandbox Q1 2027
- 6 regulatory hedges built-in (registered-form, data residency, etc.)
- Why GIFT IFIH: regulatory guidance, pilots, mentorship

### Call to Action (30 sec)
- Try live demo: http://52.6.51.39:8000
- Test credentials provided
- Contact: team@austial.com
- "Join us in building the future of RWA tokenization for India"

---

## TROUBLESHOOTING

### Frontend not loading
```bash
# Check S3 bucket
aws s3 ls s3://austial-frontend-bucket/ --profile aayush-gift

# Re-upload
cd frontend/dist/austial-app/browser
aws s3 sync . s3://austial-frontend-bucket/ --profile aayush-gift
```

### Backend API down
```bash
# SSH into EC2
ssh -i ~/.ssh/your-key.pem ec2-user@52.6.51.39

# Check container status
docker ps -a

# View logs
docker logs austial-backend

# Restart container
docker restart austial-backend
```

### Database connection errors
```bash
# Check RDS security group allows EC2 traffic
aws ec2 describe-security-groups --profile aayush-gift

# Test connection from EC2
docker exec -it austial-backend psql $DATABASE_URL -c "SELECT 1;"
```

---

## COST BREAKDOWN (Current Deployment)

| Resource | Type | Monthly Cost |
|----------|------|--------------|
| EC2 | t3.micro (1 instance) | ~$10 |
| RDS | db.t3.micro (single-AZ) | ~$15 |
| S3 | Static website hosting | ~$1 |
| ECR | Docker registry | ~$1 |
| **Total** | | **~$27/month** |

**Note:** This is a cost-capped demo deployment. Production would require:
- ECS/Fargate for auto-scaling
- Multi-AZ RDS
- CloudFront CDN
- ALB for load balancing
- Estimated production cost: $200-500/month

---

## NEXT STEPS

1. ✅ **Record pitch video** (use script template above)
2. ✅ **Upload to YouTube** and update landing page
3. ✅ **Test all flows** end-to-end (investor + admin)
4. ✅ **Submit Young Builders application** with pitch deck + video
5. ⏳ **Await sandbox approval** (Q1 2027)

---

## SUPPORT

**Technical Issues:**
- Backend: See `backend/README.md`
- Frontend: See `frontend/README.md`
- Infrastructure: See `infra/terraform/README.md`

**Pitch/Business Questions:**
- Email: team@austial.com
- Pitch Deck: `/YOUNG_BUILDERS_PITCH.md`

**Live Demo:**
- App: http://52.6.51.39:8000 (frontend + API)
- API Docs: http://52.6.51.39:8000/docs

---

**Last Updated:** 2026-08-22  
**Deployment Status:** ✅ MVP Live  
**Next Milestone:** Sandbox Application Q1 2027
