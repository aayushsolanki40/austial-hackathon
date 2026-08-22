# Austial Landing Page & Pitch Deck - Setup Guide

This guide covers the new landing page and Young Builders Program pitch deck created for Austial.

---

## 🎉 WHAT'S BEEN CREATED

### 1. **Public Landing Page** (Angular Component)
- **Location:** `frontend/src/app/features/landing/landing.component.ts`
- **Route:** `http://localhost:4200/home` (public, no auth required)
- **Features:**
  - Hero section with $10-50B TAM statistics
  - Embedded pitch video (YouTube)
  - Problem/Solution breakdown
  - Live demo walkthrough sections
  - Full Young Builders Program pitch content
  - Test credentials
  - Call-to-action for registration

### 2. **Young Builders Program Pitch Deck**
- **Location:** `YOUNG_BUILDERS_PITCH.md`
- **Format:** Markdown (convertible to PDF/slides)
- **Sections:**
  - Pitch Snapshot
  - Problem (with quantitative + qualitative data)
  - Solution (with innovation/IP)
  - Validation (customer interviews + technical metrics)
  - Regulatory Requirements
  - Team-Market Fit
  - Why GIFT IFIH?
  - Appendix (metrics, financials, contact)

### 3. **Interactive HTML Pitch Slides**
- **Location (workspace root):** `/home/aayushubuntu/Desktop/GiftFintech/austial-pitch-slides.html`
- **Usage:** Open in browser, use arrow keys to navigate
- **Features:**
  - 10 slides covering complete pitch
  - Click navigation dots
  - Keyboard controls (← → Space)
  - Print-friendly

### 4. **Standalone Landing Page** (HTML)
- **Location (workspace root):** `/home/aayushubuntu/Desktop/GiftFintech/austial-landing-page.html`
- **Usage:** Can be deployed separately to any web server
- **Features:** Same content as Angular component, no framework dependencies

### 5. **Documentation**
- `DEPLOYMENT_GUIDE.md` — How to build & deploy to AWS
- `VIDEO_GUIDE.md` — Script + instructions for recording pitch video
- `scripts/deploy.sh` — Automated deployment script

---

## 🚀 QUICK START

### Local Development

```bash
# Terminal 1: Backend
cd backend
uv sync
uv run austial serve
# → http://localhost:8000

# Terminal 2: Frontend
cd frontend
npm install
npm start
# → http://localhost:4200
```

**Landing page:** http://localhost:4200/home

### View Pitch Materials

```bash
# Open pitch slides in browser
open /home/aayushubuntu/Desktop/GiftFintech/austial-pitch-slides.html
# (Use arrow keys to navigate)

# Read markdown pitch deck
cat YOUNG_BUILDERS_PITCH.md

# Open standalone landing page
open /home/aayushubuntu/Desktop/GiftFintech/austial-landing-page.html
```

---

## 📹 CREATE PITCH VIDEO (CRITICAL STEP)

The landing page has a **placeholder YouTube video**. Follow these steps to replace it:

### Step 1: Record Video (8-10 minutes)

Follow the detailed script in `VIDEO_GUIDE.md`. Key sections:

1. **Opening** (30s) — Hook with $10-50B TAM
2. **Problem** (2min) — Investor/issuer pain points
3. **Solution Demo** (4-5min) — Live walkthrough of http://52.6.51.39:8000
4. **Tech & Validation** (2min) — 24 entities, 8 interviews, competitive positioning
5. **Regulatory & Team** (1.5min) — IFSCA pathway, why GIFT IFIH
6. **Call to Action** (30s) — Try demo, contact info

**Tools:**
- Screen recording: OBS Studio (free) or Loom
- Editing: iMovie, DaVinci Resolve, or OpenShot
- Export: 1080p MP4

### Step 2: Upload to YouTube

```
Title: Austial - RWA Tokenization Platform for GIFT City | Young Builders Program 2026

Description:
Austial is a GIFT City-based IFSCA-compliant platform enabling fractional 
ownership of Indian real estate, commodities, and infrastructure.

Live Demo: http://52.6.51.39:8000
Test Credentials: investor@test.com / password123
Pitch Deck: [link to GitHub]

Contact: team@austial.com

Tags: IFSCA, GIFT City, RWA, tokenization, fintech, Young Builders
```

### Step 3: Update Landing Page

```typescript
// File: frontend/src/app/features/landing/landing.component.ts
// Line ~95 (search for "dQw4w9WgXcQ"):

src="https://www.youtube.com/embed/YOUR_VIDEO_ID_HERE"

// Save file
```

### Step 4: Rebuild & Deploy

```bash
cd frontend
npm run build

# Deploy (choose one method):

# Method 1: Automated script
cd ..
./scripts/deploy.sh

# Method 2: Manual
cd infra/terraform
terraform init
terraform apply
```

---

## 🌐 DEPLOYMENT

### Option A: Automated Script (Recommended)

```bash
cd /home/aayushubuntu/Desktop/GiftFintech/austial-hackathon
./scripts/deploy.sh
```

This will:
1. Build frontend → deploy to S3
2. Build backend Docker image → push to ECR
3. Deploy to EC2
4. Run database migrations
5. Verify endpoints

### Option B: Manual Deployment

See `DEPLOYMENT_GUIDE.md` for step-by-step instructions.

### Option C: Use Sync Skill

```bash
# In Claude Code session:
> use the sync-aws-infra skill to deploy the latest changes
```

---

## 🧪 TESTING

### Test Landing Page Locally

```bash
cd frontend
npm start
open http://localhost:4200/home
```

**Check:**
- [ ] Hero section loads with stats
- [ ] Video iframe shows (placeholder for now)
- [ ] Problem/Solution sections render
- [ ] Navigation links work
- [ ] "Launch App" button goes to /login
- [ ] "Create Free Account" button goes to /register

### Test Landing Page on Production

```bash
# After deployment
open http://austial-frontend-bucket.s3-website-us-east-1.amazonaws.com/home
```

### Test Full App Flow

1. **Go to:** http://52.6.51.39:8000/home (landing page)
2. **Click:** "Create Free Account"
3. **Register** with test email
4. **Complete KYC** (upload sample documents)
5. **Browse marketplace**
6. **Subscribe to asset**
7. **View portfolio**
8. **Request redemption**

### Test Admin Flow

1. **Login as:** admin@test.com / password123
2. **Check dashboard** (KPIs load)
3. **Approve KYC** submission
4. **View AML alerts**
5. **Generate compliance report**

---

## 📊 PITCH DECK FORMATS

The pitch content is available in multiple formats:

### 1. Markdown Document
- **File:** `YOUNG_BUILDERS_PITCH.md`
- **Use:** Email, GitHub, documentation
- **Convert to PDF:**
  ```bash
  pandoc YOUNG_BUILDERS_PITCH.md -o pitch.pdf --toc
  ```

### 2. Interactive HTML Slides
- **File:** `/home/aayushubuntu/Desktop/GiftFintech/austial-pitch-slides.html`
- **Use:** Presenting to audience
- **Controls:** Arrow keys, space, click dots

### 3. Embedded in Landing Page
- **URL:** http://52.6.51.39:8000/home#pitch
- **Use:** Shareable link with embedded content

### 4. Standalone Landing Page
- **File:** `/home/aayushubuntu/Desktop/GiftFintech/austial-landing-page.html`
- **Use:** Host anywhere (no Angular needed)
- **Deploy:** 
  ```bash
  cp /home/aayushubuntu/Desktop/GiftFintech/austial-landing-page.html ~/Desktop/
  # Upload to Netlify, Vercel, or any static host
  ```

---

## 🎨 CUSTOMIZATION

### Update Video Link

```typescript
// frontend/src/app/features/landing/landing.component.ts
// Line ~95:
src="https://www.youtube.com/embed/YOUR_VIDEO_ID"
```

### Update Stats

```typescript
// frontend/src/app/features/landing/landing.component.ts
// Search for "Key Stats" section (~line 50):

<div class="text-5xl font-bold text-yellow-300">$10-50B</div>
<div class="text-5xl font-bold text-yellow-300">5-6 sec</div>
<div class="text-5xl font-bold text-yellow-300">&lt;1%</div>
<div class="text-5xl font-bold text-yellow-300">24</div>
```

### Update Contact Info

```typescript
// Search for "team@austial.com" and replace:
team@austial.com → your-email@domain.com
```

### Change Colors

```typescript
// In component styles (bottom of landing.component.ts):

.gradient-bg {
  background: linear-gradient(135deg, #0B4F6C 0%, #01BAEF 100%);
  // Change these hex codes
}
```

---

## 📋 CHECKLIST FOR YOUNG BUILDERS SUBMISSION

Before submitting your application:

### Content
- [ ] Recorded 8-10 minute pitch video
- [ ] Uploaded video to YouTube
- [ ] Updated video link in landing page
- [ ] Reviewed pitch deck markdown (YOUNG_BUILDERS_PITCH.md)
- [ ] Verified all stats are accurate

### Technical
- [ ] Landing page deployed to AWS
- [ ] Video embeds correctly on landing page
- [ ] Live demo works end-to-end (test all flows)
- [ ] Test credentials work (investor + admin)
- [ ] API docs accessible (http://52.6.51.39:8000/docs)

### Documentation
- [ ] README updated with current info
- [ ] Pitch deck has correct contact email
- [ ] All links in pitch deck are live
- [ ] Screenshots/demos in video show live system (not mockups)

### Submission Materials
- [ ] Pitch deck (PDF or markdown)
- [ ] Pitch video (YouTube link)
- [ ] Live demo URL (http://52.6.51.39:8000)
- [ ] Landing page URL
- [ ] Test credentials documented
- [ ] GitHub repo link (if applicable)

---

## 🆘 TROUBLESHOOTING

### "Landing page not loading"

```bash
# Check Angular routing
cd frontend
grep -r "landing" src/app/app.routes.ts

# Should see:
# { path: 'home', loadComponent: () => import('./features/landing/landing.component')...

# Rebuild
npm run build
```

### "Video not embedding"

1. Check YouTube video is **not private** (must be "Public" or "Unlisted")
2. Verify video ID is correct: `https://youtube.com/watch?v=VIDEO_ID`
3. Check iframe src: `https://www.youtube.com/embed/VIDEO_ID` (not `/watch?v=`)

### "Deployment failed"

```bash
# Check AWS credentials
aws sts get-caller-identity --profile aayush-gift

# Check Docker daemon
docker ps

# Re-run deployment
./scripts/deploy.sh
```

### "Angular build errors"

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

---

## 📞 SUPPORT

**Technical Issues:**
- Backend: See `backend/README.md`
- Frontend: See `frontend/README.md`
- Deployment: See `DEPLOYMENT_GUIDE.md`
- Video: See `VIDEO_GUIDE.md`

**Pitch/Business Questions:**
- Pitch Deck: `YOUNG_BUILDERS_PITCH.md`
- Email: team@austial.com

**Live URLs:**
- Landing Page: http://austial-frontend-bucket.s3-website-us-east-1.amazonaws.com/home
- Live App: http://52.6.51.39:8000
- API Docs: http://52.6.51.39:8000/docs
- Pitch Slides: Open `/austial-pitch-slides.html` in browser

---

## 📁 FILE LOCATIONS SUMMARY

```
austial-hackathon/
├── frontend/
│   └── src/app/features/landing/
│       └── landing.component.ts          ← Angular landing page component
├── YOUNG_BUILDERS_PITCH.md               ← Markdown pitch deck
├── DEPLOYMENT_GUIDE.md                   ← Deployment instructions
├── VIDEO_GUIDE.md                        ← Video recording script
├── LANDING_PAGE_README.md                ← This file
└── scripts/
    └── deploy.sh                         ← Automated deployment

/home/aayushubuntu/Desktop/GiftFintech/
├── austial-pitch-slides.html             ← Interactive HTML slides
├── austial-landing-page.html             ← Standalone HTML landing page
└── AUSTIAL_YOUNG_BUILDERS_PITCH.md       ← Alternate pitch deck location
```

---

## ✅ NEXT STEPS

1. **Record pitch video** using `VIDEO_GUIDE.md` script
2. **Upload to YouTube** and get video ID
3. **Update landing page** with video ID
4. **Test locally** (http://localhost:4200/home)
5. **Deploy to AWS** (`./scripts/deploy.sh`)
6. **Verify live** (http://52.6.51.39:8000)
7. **Submit Young Builders application** with:
   - Pitch video link
   - Live demo URL
   - Pitch deck (YOUNG_BUILDERS_PITCH.md)
   - Landing page URL

---

**Built with ❤️ for GIFT City | Ready for Young Builders Program Q1 2027**

*For questions: team@austial.com*
