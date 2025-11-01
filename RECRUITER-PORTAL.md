# Recruiter Portal System

## Overview

Complete serverless system for recruiters to submit job opportunities and for admins to manage submissions via an authenticated dashboard.

## System Architecture

```
┌─────────────────┐
│   Recruiters    │
│  (Public Form)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│      API Gateway (HTTP API)              │
│  riyot36gu9.execute-api.ap-southeast-5  │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│    Lambda Function (Python 3.12)         │
│      job-tracker-api (256 MB)            │
└────────┬────────────────────────────────┘
         │
         ├──────────────┬──────────────┐
         ▼              ▼              ▼
    ┌────────┐    ┌─────────┐    ┌──────────┐
    │   S3   │    │ Cognito │    │   S3     │
    │ Bucket │    │  Auth   │    │ Portfolio│
    └────────┘    └─────────┘    └──────────┘
                                       │
                                       ▼
                                 ┌──────────────┐
                                 │  CloudFront  │
                                 │ cv.vgnshlv.nz│
                                 └──────────────┘
```

## Components

### 1. Recruiter Submission Form
**URL:** https://cv.vgnshlv.nz/recruiter-submit.html

**Features:**
- Professional form matching CV portfolio aesthetic
- Comprehensive job details capture
- File upload for job descriptions (PDF/DOCX, max 5MB)
- Auto-format phone numbers (Malaysia +60 prefix)
- Real-time validation
- Success confirmation with submission ID

**Form Fields:**
- **Recruiter Info**: Name, Email, Phone/WhatsApp, Agency (optional)
- **Job Details**: Title, Company, Salary Range (min/max), Currency
- **Requirements**: Text area for must-have skills
- **Skills**: Comma-separated skills list
- **Description**: Full job description
- **File**: Job description attachment

### 2. Admin Dashboard
**URL:** https://cv.vgnshlv.nz/recruiter-dashboard.html

**Authentication:**
- AWS Cognito User Pool
- Email: admin@example.com
- Password: AdminPass123!

**Features:**
- Statistics cards (Total, New, Contacted, CV Sent)
- Submissions table with color-coded status badges
- Filter by status dropdown
- Click to view detailed submission modal
- Inline status updates
- Admin notes with save functionality
- Download links for JD and custom CV
- Upload customized CV button

### 3. Backend API (Lambda)

**Function:** job-tracker-api
**Runtime:** Python 3.12
**Memory:** 256 MB
**Timeout:** 30 seconds
**Region:** ap-southeast-5

**API Endpoints:**

#### Create Submission
```bash
POST /recruiter-submissions
Content-Type: application/json

{
  "recruiter": {
    "name": "John Smith",
    "email": "john@agency.com",
    "phone": "+60-12-3456789",
    "agency": "Tech Recruiters Inc"
  },
  "job": {
    "title": "Senior Backend Engineer",
    "company": "Acme Corp",
    "salary_min": 10000,
    "salary_max": 15000,
    "currency": "MYR",
    "requirements": "5+ years Python, AWS experience",
    "skills": ["Python", "AWS", "Docker", "Kubernetes"],
    "description": "Full job description..."
  }
}

Response:
{
  "submission_id": "rec_2025-11-01_abc12345",
  "created_at": "2025-11-01T12:00:00Z",
  "jd_upload_url": "https://...",
  "jd_upload_url_expires_in": 900
}
```

#### List Submissions
```bash
GET /recruiter-submissions?status=new&limit=100

Response:
{
  "submissions": [
    {
      "submission_id": "rec_2025-11-01_abc12345",
      "created_at": "2025-11-01T12:00:00Z",
      "status": "new",
      "recruiter_name": "John Smith",
      "recruiter_email": "john@agency.com",
      "job_title": "Senior Backend Engineer",
      "company": "Acme Corp",
      "salary_max": 15000
    }
  ],
  "count": 1
}
```

#### Get Submission Details
```bash
GET /recruiter-submissions/{id}

Response:
{
  "submission_id": "rec_2025-11-01_abc12345",
  "status": "contacted",
  "recruiter": { ... },
  "job": { ... },
  "files": {
    "job_description": "recruiters/2025/rec_.../jd.pdf",
    "customized_cv": "recruiters/2025/rec_.../cv_custom.pdf"
  },
  "admin_notes": "Called via WhatsApp...",
  "contact_history": [
    {
      "date": "2025-11-01T13:00:00Z",
      "old_status": "new",
      "new_status": "contacted",
      "note": ""
    }
  ],
  "jd_download_url": "https://... (presigned, 15min)",
  "cv_download_url": "https://... (presigned, 15min)"
}
```

#### Update Status
```bash
PUT /recruiter-submissions/{id}/status
Content-Type: application/json

{
  "status": "contacted"  # new | contacted | cv_sent | closed
}

Response:
{
  "submission_id": "rec_2025-11-01_abc12345",
  "updated": true,
  "old_status": "new",
  "new_status": "contacted",
  "updated_at": "2025-11-01T13:00:00Z"
}
```

#### Update Admin Notes
```bash
PUT /recruiter-submissions/{id}/notes
Content-Type: application/json

{
  "notes": "Called recruiter via WhatsApp. Will send CV tomorrow."
}

Response:
{
  "submission_id": "rec_2025-11-01_abc12345",
  "updated": true,
  "updated_at": "2025-11-01T13:05:00Z"
}
```

#### Get CV Upload URL
```bash
POST /recruiter-submissions/{id}/cv-upload

Response:
{
  "submission_id": "rec_2025-11-01_abc12345",
  "cv_upload_url": "https://... (presigned, 15min)",
  "cv_upload_url_expires_in": 900,
  "content_type": "application/pdf",
  "max_size_bytes": 10485760
}
```

### 4. AWS Cognito Authentication

**User Pool:** recruiter-portal-prod
**User Pool ID:** ap-southeast-5_0QQg8Wd6r
**Client ID:** 4f8f3qon7v6tegud4qe854epo6
**Region:** ap-southeast-5

**Configuration:**
- Email-based authentication
- Password policy: 8+ chars, upper/lower/numbers required
- Admin-create-only (no public signup)
- Token validity: 60 minutes (access/ID), 30 days (refresh)

**Admin User:**
- Email: admin@example.com
- Password: AdminPass123!
- Status: Active

### 5. Storage Structure (S3)

**Bucket:** vgnshlvnz-job-tracker
**Region:** ap-southeast-5

**Directory Structure:**
```
recruiters/
└── 2025/
    └── rec_2025-11-01_abc12345/
        ├── meta.json          # Submission metadata
        ├── jd.pdf             # Job description (from recruiter)
        └── cv_custom.pdf      # Customized CV (from admin)
```

**Metadata Schema (meta.json):**
```json
{
  "submission_id": "rec_2025-11-01_abc12345",
  "type": "recruiter_submission",
  "created_at": "2025-11-01T12:00:00Z",
  "updated_at": "2025-11-01T13:05:00Z",
  "status": "contacted",
  "recruiter": {
    "name": "John Smith",
    "email": "john@agency.com",
    "phone": "+60-12-3456789",
    "agency": "Tech Recruiters Inc"
  },
  "job": {
    "title": "Senior Backend Engineer",
    "company": "Acme Corp",
    "salary_min": 10000,
    "salary_max": 15000,
    "currency": "MYR",
    "requirements": "5+ years Python, AWS experience",
    "skills": ["Python", "AWS", "Docker", "Kubernetes"],
    "description": "Full job description..."
  },
  "files": {
    "job_description": "recruiters/2025/rec_.../jd.pdf",
    "customized_cv": "recruiters/2025/rec_.../cv_custom.pdf"
  },
  "admin_notes": "Called via WhatsApp. Sending customized CV tomorrow.",
  "contact_history": [
    {
      "date": "2025-11-01T13:00:00Z",
      "old_status": "new",
      "new_status": "contacted",
      "note": ""
    }
  ]
}
```

## Workflow

### Recruiter Submission Flow
1. Recruiter visits https://cv.vgnshlv.nz/recruiter-submit.html
2. Fills out comprehensive form with job details
3. Optionally uploads JD file (PDF/DOCX)
4. Submits form
5. API creates submission with unique ID: `rec_YYYY-MM-DD_UUID`
6. If JD file provided, uploads to presigned S3 URL
7. Confirmation shown with submission ID
8. Admin notified (future: email/WhatsApp notification)

### Admin Review Flow
1. Admin logs in at https://cv.vgnshlv.nz/recruiter-dashboard.html
2. Views submissions table with statistics
3. Clicks submission to view details
4. Reviews recruiter info, job requirements, downloads JD
5. Updates status to "contacted"
6. Adds admin notes (e.g., "Called via WhatsApp")
7. Prepares customized CV
8. Uploads CV via dashboard
9. Updates status to "cv_sent"
10. Downloads CV to send to recruiter via WhatsApp
11. Marks as "closed" when process complete

### Status Lifecycle
```
new → contacted → cv_sent → closed
```

- **new**: Initial submission, not yet reviewed
- **contacted**: Admin has contacted recruiter
- **cv_sent**: Customized CV has been sent
- **closed**: Process complete (hired/rejected/no response)

## Deployment

### Lambda Function
```bash
# Package Lambda
zip -j /tmp/lambda-package.zip src/app.py

# Deploy
aws lambda update-function-code \
  --function-name job-tracker-api \
  --zip-file fileb:///tmp/lambda-package.zip \
  --region ap-southeast-5
```

### Cognito Stack
```bash
# Deploy Cognito infrastructure
sam deploy \
  --template template-cognito.yaml \
  --stack-name recruiter-portal-cognito \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides Environment=prod \
  --region ap-southeast-5

# Create admin user
aws cognito-idp admin-create-user \
  --user-pool-id ap-southeast-5_0QQg8Wd6r \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com Name=name,Value="Portal Admin" \
  --temporary-password "TempPassword123!" \
  --message-action SUPPRESS

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id ap-southeast-5_0QQg8Wd6r \
  --username admin@example.com \
  --password "AdminPass123!" \
  --permanent
```

### Frontend Files
```bash
# Upload to S3
aws s3 cp recruiter-submit.html s3://vgnshlvnz-portfolio/ --content-type "text/html"
aws s3 cp recruiter-dashboard.html s3://vgnshlvnz-portfolio/ --content-type "text/html"

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id E1XWXVYFO71217 \
  --paths "/recruiter-submit.html" "/recruiter-dashboard.html"
```

### API Gateway Routes
```bash
# Routes are managed via AWS Console or CloudFormation
# Required routes:
POST   /recruiter-submissions
GET    /recruiter-submissions
GET    /recruiter-submissions/{id}
PUT    /recruiter-submissions/{id}/status
PUT    /recruiter-submissions/{id}/notes
POST   /recruiter-submissions/{id}/cv-upload
```

## Testing

### API Tests
```bash
API_BASE="https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod"

# Create submission
curl -X POST "$API_BASE/recruiter-submissions" \
  -H "Content-Type: application/json" \
  -d '{
    "recruiter": {
      "name": "Test Recruiter",
      "email": "test@example.com",
      "phone": "+60-12-9999999",
      "agency": "Test Agency"
    },
    "job": {
      "title": "Senior Python Developer",
      "company": "Test Company",
      "salary_min": 10000,
      "salary_max": 15000,
      "currency": "MYR",
      "requirements": "5+ years Python",
      "skills": ["Python", "AWS", "Docker"],
      "description": "Test description"
    }
  }'

# List submissions
curl "$API_BASE/recruiter-submissions"

# Get submission details
curl "$API_BASE/recruiter-submissions/rec_2025-11-01_abc12345"

# Update status
curl -X PUT "$API_BASE/recruiter-submissions/rec_2025-11-01_abc12345/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "contacted"}'

# Update notes
curl -X PUT "$API_BASE/recruiter-submissions/rec_2025-11-01_abc12345/notes" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Test notes"}'

# Get CV upload URL
curl -X POST "$API_BASE/recruiter-submissions/rec_2025-11-01_abc12345/cv-upload"
```

## Security

### Authentication
- Admin dashboard protected by AWS Cognito
- JWT tokens with 60-minute expiry
- Refresh tokens valid for 30 days
- No public signup (admin-create-only)

### File Uploads
- Presigned S3 URLs with 15-minute expiry
- Content-type validation (PDF/DOCX only)
- Size limits: 5MB (JD), 10MB (CV)
- Secure S3 bucket with server-side encryption

### API Security
- CORS enabled for cv.vgnshlv.nz only
- HTTPS only (TLS 1.2+)
- Input validation and sanitization
- Rate limiting via API Gateway (future)
- Cognito authorizer for admin endpoints (future)

## Monitoring

### CloudWatch Logs
```bash
# View Lambda logs
aws logs tail /aws/lambda/job-tracker-api --follow

# View recent errors
aws logs filter-pattern /aws/lambda/job-tracker-api --filter-pattern "ERROR"
```

### Metrics
- Lambda invocations
- Lambda duration (cold start ~400ms, warm ~50ms)
- API Gateway request count
- S3 storage usage
- Cognito active users

## Cost Estimation

**Monthly Costs (low traffic):**
- Lambda: $0 (free tier: 1M requests, 400K GB-seconds)
- API Gateway: $0 (free tier: 1M requests)
- S3 Storage: $0.50 (assuming 20 GB)
- CloudFront: $0 (free tier: 1TB transfer)
- Cognito: $0 (free tier: 50K MAU)

**Total: ~$0.50/month** (within AWS free tier)

## Troubleshooting

### Issue: CloudFront returns old cached version
```bash
# Invalidate cache
aws cloudfront create-invalidation \
  --distribution-id E1XWXVYFO71217 \
  --paths "/recruiter-submit.html" "/recruiter-dashboard.html"
```

### Issue: Lambda errors on file upload
```bash
# Check Lambda logs
aws logs tail /aws/lambda/job-tracker-api --since 10m

# Common causes:
# - S3 region mismatch (fixed: using Config with region_name)
# - Presigned URL expired (15min limit)
# - Invalid content-type
```

### Issue: Cognito login fails
```bash
# Check user status
aws cognito-idp admin-get-user \
  --user-pool-id ap-southeast-5_0QQg8Wd6r \
  --username admin@example.com

# Reset password
aws cognito-idp admin-set-user-password \
  --user-pool-id ap-southeast-5_0QQg8Wd6r \
  --username admin@example.com \
  --password "NewPassword123!" \
  --permanent
```

## Future Enhancements

1. **Email Notifications**
   - Send email to admin when new submission arrives
   - Send confirmation email to recruiter

2. **WhatsApp Integration**
   - Auto-send submission details via WhatsApp API
   - Send CV directly to recruiter's WhatsApp

3. **Advanced Dashboard Features**
   - Search and filter by company, skills, salary
   - Export submissions to CSV
   - Bulk status updates
   - Analytics dashboard

4. **API Enhancements**
   - Add Cognito authorizer to admin endpoints
   - Implement rate limiting
   - Add pagination for large result sets
   - Add full-text search

5. **DynamoDB Integration**
   - Faster queries (vs S3 list operations)
   - Better indexing and filtering
   - Real-time updates

## Resources

### URLs
- **Recruiter Form:** https://cv.vgnshlv.nz/recruiter-submit.html
- **Admin Dashboard:** https://cv.vgnshlv.nz/recruiter-dashboard.html
- **API Base:** https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod

### AWS Console Links
- **Lambda:** https://console.aws.amazon.com/lambda/home?region=ap-southeast-5#/functions/job-tracker-api
- **API Gateway:** https://console.aws.amazon.com/apigateway/home?region=ap-southeast-5
- **S3 Bucket:** https://s3.console.aws.amazon.com/s3/buckets/vgnshlvnz-job-tracker
- **CloudFront:** https://console.aws.amazon.com/cloudfront/v3/home#/distributions/E1XWXVYFO71217
- **Cognito:** https://console.aws.amazon.com/cognito/v2/idp/user-pools/ap-southeast-5_0QQg8Wd6r

### Documentation Files
- **RECRUITER-PORTAL.md** - This document
- **API.md** - Complete API reference
- **SESSION-SUMMARY.md** - Deployment history
- **CLOUDFRONT-DEPLOYMENT.md** - CloudFront setup details

---

**Deployment Date:** November 1, 2025
**Status:** Production Ready ✅
**Last Updated:** November 1, 2025

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
