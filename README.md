# Vigneshwaran Ravichandran - CV Portfolio & Job Tracker

Personal CV portfolio website with Unix man page aesthetic + Serverless job application tracking system - optimized for AWS.

## 🎯 Overview

Complete serverless system featuring:
- **CV Portfolio**: Static website with Unix man page aesthetic hosted on S3 + CloudFront
- **Job Tracker**: RESTful API for tracking job applications with S3 storage
- **Infrastructure as Code**: SAM templates for reproducible deployments
- **Cost Optimized**: Free-tier eligible, ~$0-2 USD/month after

**Live**: https://cv.vgnshlv.nz
**API**: https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod

## 📋 Content Sections

✅ **NAME** - Professional identity and title
✅ **CONTACT** - Contact information
✅ **OPTIONS** - Navigation menu
✅ **SYNOPSIS** - Professional summary
✅ **SKILLS** - Technical expertise organized by category
✅ **EXPERIENCE** - Comprehensive work history with expandable details
✅ **PROJECTS** - Key projects and technical achievements
✅ **EDUCATION** - Academic background and certifications
✅ **PHILOSOPHY** - Professional approach and core principles
✅ **SEE ALSO** - Additional links

## 🛠️ Technical Implementation

### Design Philosophy
- **Unix Man Page Aesthetic** - Clean, minimalist design
- **Liberation Fonts** - Authentic Unix typography
- **Monochrome Palette** - Professional appearance
- **No Framework Dependencies** - Pure HTML/CSS/JS

### Key Features
- ✅ Responsive design for all devices
- ✅ Expandable experience timeline
- ✅ Interactive skill sections
- ✅ CV download modal
- ✅ Smooth scrolling navigation
- ✅ Keyboard accessibility
- ✅ SEO optimized

### File Structure
```
vgnshlvnz-s3-bucket/
├── Infrastructure as Code
│   ├── template-portfolio.yaml        # Portfolio SAM template
│   ├── template-job-tracker.yaml      # Job tracker SAM template
│   ├── samconfig.toml                 # Multi-env deployment configs
│   └── deploy.sh                      # Automated deployment script
│
├── Lambda Function
│   └── src/
│       └── app.py                     # Job tracker API (Python 3.12)
│
├── Frontend
│   ├── index.html                     # CV portfolio page
│   ├── apply.html                     # Job submission form
│   ├── job-tracker.html               # Admin tracker view
│   ├── css/style.css                  # Unix man page styling
│   └── js/
│       ├── script.js                  # Portfolio interactivity
│       └── job-tracker.js             # Tracker functionality
│
├── Documentation
│   ├── README.md                      # This file
│   ├── API.md                         # Complete API documentation
│   ├── QUICKSTART.md                  # 30-minute deployment guide
│   ├── IMPLEMENTATION-SUMMARY.md      # Full implementation summary
│   ├── DNS-SETUP.md                   # Cloudflare DNS configuration
│   ├── COST-SETUP.md                  # Cost monitoring & optimization
│   └── POST-DNS-CHECKLIST.md          # Verification checklist
│
└── Static Assets
    ├── images/                        # Profile images
    └── downloads/                     # CV files (PDF/DOCX)
```

## 🏗️ Architecture

### System Overview

```
                        ┌─────────────────────┐
                        │   Cloudflare DNS    │
                        │  cv.vgnshlv.nz      │
                        └──────────┬──────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
             ┌──────▼───────┐           ┌────────▼────────┐
             │  CloudFront  │           │   API Gateway   │
             │  (CDN + SSL) │           │   (HTTP API)    │
             └──────┬───────┘           └────────┬────────┘
                    │                            │
             ┌──────▼───────┐           ┌────────▼────────┐
             │      S3      │           │  Lambda (ARM64) │
             │   Portfolio  │           │  Python 3.12    │
             └──────────────┘           └────────┬────────┘
                                                 │
                                         ┌───────▼────────┐
                                         │       S3       │
                                         │  Job Tracker   │
                                         │ (apps + CVs)   │
                                         └────────────────┘
```

### Portfolio Stack

- **S3 Bucket**: `vgnshlvnz-portfolio` - Static website hosting
- **CloudFront**: Global CDN with HTTP/2 and HTTP/3
- **ACM Certificate**: SSL/TLS for custom domain
- **Route53**: DNS management (optional, using Cloudflare)

### Job Tracker Stack

- **API Gateway**: HTTP API (cheaper than REST)
- **Lambda**: ARM64/Graviton2 for 20% cost savings
- **S3 Bucket**: `vgnshlvnz-job-tracker` - Application storage
- **CloudWatch**: Logs retention (7-14 days)
- **Optional**: DynamoDB for fast querying (disabled by default)

### Data Flow

1. **Job Submission**: Recruiter fills form → POST /applications
2. **Metadata Storage**: Lambda writes JSON to S3
3. **CV Upload**: Presigned URL → Direct S3 upload (no Lambda)
4. **Retrieval**: GET /applications → Lambda reads S3 metadata
5. **CV Download**: Presigned URL → Direct S3 download

### Cost Optimization Features

✅ ARM64 Lambda (20% cheaper + faster)
✅ HTTP API vs REST API (60% cheaper)
✅ Presigned URLs (bypass Lambda for files)
✅ Intelligent-Tiering storage
✅ Short log retention (7-14 days)
✅ S3 lifecycle policies (auto-cleanup)
✅ Pay-per-use pricing (no always-on costs)

**Expected cost**: $0/month (free tier) → ~$0.17 USD/month after

## 🚀 Quick Start

### Get Live in 30 Minutes

```bash
# 1. Configure DNS (Cloudflare) - see DNS-SETUP.md
# 2. Deploy job tracker
./deploy.sh job-tracker prod

# 3. Sync portfolio files
./deploy.sh sync

# 4. Test API
curl https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications
```

**Full guide**: See [QUICKSTART.md](QUICKSTART.md)

### API Endpoints

```bash
BASE_URL="https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod"

# Create application
POST   /applications

# List applications (with optional ?status=applied&limit=100)
GET    /applications

# Get single application
GET    /applications/{id}

# Update application
PUT    /applications/{id}

# Delete application
DELETE /applications/{id}

# Get fresh CV upload URL
POST   /applications/{id}/cv-upload-url
```

**Full API docs**: See [API.md](API.md)

## 🚀 Deployment (Detailed)

### Prerequisites
- AWS CLI configured (`aws configure`)
- SAM CLI installed (`sam --version`)
- Cloudflare account (for DNS)

### Portfolio Deployment

The website is optimized for AWS S3 static hosting:
- No server-side dependencies
- Fast loading with minimal external requests
- Liberation fonts via Google Fonts CDN
- Mobile-first responsive design

## 📱 Experience Timeline

Comprehensive work history from current L2 Engineer position at Trovicor Intelligence through previous roles at:
- Trovicor Intelligence (L1 Support Lead)
- Datacom (Business Support System Engineer)
- STL - Sterlite Technologies (System Engineer)
- CGI, Seagate Technology, HPE, Hewlett-Packard

## 🎓 Certifications

- Red Hat Certified System Administrator (RHCSA)
- Red Hat Specialist in Virtualization
- Red Hat Specialist in Containers
- Diploma in Information Technology - Asia Pacific University (2020)

---

**Live Preview**: Ready for AWS S3 deployment
**Repository**: https://github.com/vgnshlvnz/vgnshlvnz-s3-cv
**Last Updated**: November 2025
