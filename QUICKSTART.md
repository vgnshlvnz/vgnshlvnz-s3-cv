# Quick Start Guide

## Get cv.vgnshlv.nz Live in 30 Minutes

This guide will get your CV portfolio and job tracker system deployed and operational.

---

## Prerequisites Checklist

- [ ] AWS account with CLI configured (`aws configure`)
- [ ] SAM CLI installed (`sam --version`)
- [ ] Domain access in Cloudflare (vgnshlv.nz)
- [ ] Git repository cloned locally
- [ ] Basic understanding of AWS services

---

## Step 1: DNS Configuration (5 minutes)

### Add SSL Validation Record

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select domain: `vgnshlv.nz`
3. Go to **DNS** → **Records** → **Add record**

```
Type:    CNAME
Name:    _09870b99f2b91d081db38b5ac73c4832.cv
Target:  _ae18afce56fdbca76320361b0076a2e8.jkddzztszm.acm-validations.aws.
TTL:     Auto
Proxy:   DNS only (grey cloud)
```

4. Click **Save**

### Add CV Subdomain Record

1. Still in DNS, click **Add record**

```
Type:    CNAME
Name:    cv
Target:  d1cda43lowke66.cloudfront.net
TTL:     Auto
Proxy:   Proxied (orange cloud ON)
```

2. Click **Save**

### Verify DNS Propagation

```bash
# Wait 2-5 minutes, then check:
dig cv.vgnshlv.nz +short

# Should show Cloudflare IPs or CloudFront domain
```

---

## Step 2: Verify SSL Certificate (5-30 minutes)

```bash
# Check certificate status
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:460742884565:certificate/eca0af92-5e9e-4e06-a658-ca38bfa5b8c5 \
  --region us-east-1 \
  --query 'Certificate.Status' \
  --output text

# Expected: ISSUED (may take 5-30 minutes after DNS config)
```

**While waiting**, continue to Step 3.

---

## Step 3: Deploy Job Tracker Lambda (10 minutes)

### Validate Templates

```bash
cd /home/agh0ri/vgnshlvnz-s3-bucket

# Validate both SAM templates
./deploy.sh validate

# Expected: ✅ All templates validated successfully
```

### Deploy Job Tracker

```bash
# Deploy to production
./deploy.sh job-tracker prod

# You'll see:
# 1. SAM building Lambda package
# 2. CloudFormation changeset preview
# 3. Confirmation prompt
# 4. Deployment progress
# 5. Stack outputs (API endpoint, bucket name, etc.)
```

**Expected output:**
```
ApiEndpoint: https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod
BucketName: vgnshlvnz-job-tracker
FunctionArn: arn:aws:lambda:ap-southeast-5:...:function:vgnshlvnz-job-tracker-api
```

**Copy the API endpoint!** You'll need it for testing.

---

## Step 4: Test the API (5 minutes)

### Test 1: List Applications

```bash
API_BASE="https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod"

curl "$API_BASE/applications" | jq '.'
```

**Expected:**
```json
{
  "applications": [],
  "count": 0,
  "filters": {
    "status": null,
    "limit": 100
  }
}
```

### Test 2: Create Application

```bash
curl -X POST "$API_BASE/applications" \
  -H "Content-Type: application/json" \
  -d '{
    "job_title": "DevOps Engineer",
    "company_name": "Test Company",
    "caller": {
      "name": "Test Recruiter",
      "email": "test@example.com",
      "phone": "+60-12-3456789"
    },
    "caller_method": "email",
    "salary": {
      "currency": "MYR",
      "min": 8000,
      "max": 12000,
      "period": "monthly"
    },
    "details": {
      "skillsets": ["AWS", "Docker", "Python"]
    },
    "tags": ["test"]
  }' | jq '.'
```

**Expected:**
```json
{
  "application_id": "app_2025-11-01_abc12345",
  "cv_upload_url": "https://vgnshlvnz-job-tracker.s3...",
  "cv_upload_url_expires_in": 900,
  "created_at": "2025-11-01T10:22:15Z"
}
```

### Test 3: Upload CV (Optional)

```bash
# Save the application_id and cv_upload_url from above
APP_ID="app_2025-11-01_abc12345"
CV_UPLOAD_URL="<url_from_above>"

# Upload a test PDF
curl -X PUT "$CV_UPLOAD_URL" \
  -H "Content-Type: application/pdf" \
  --data-binary @"downloads/vigneshwaran_cv.pdf"

# Expected: No output = success (200 OK)
```

### Test 4: Get Application with CV Download

```bash
curl "$API_BASE/applications/$APP_ID" | jq '.'
```

**Expected:** Full application object with `cv_download_url`

---

## Step 5: Sync Portfolio Files to S3 (2 minutes)

```bash
# Sync static files to S3 bucket
./deploy.sh sync

# This will:
# 1. Upload index.html, apply.html, CSS, JS, images
# 2. Invalidate CloudFront cache
# 3. Changes live in 1-2 minutes
```

**Verify:**
```bash
# Check S3 website endpoint
curl -I http://vgnshlvnz-portfolio.s3-website.ap-southeast-5.amazonaws.com

# Expected: HTTP/1.1 200 OK
```

---

## Step 6: Test CV Portfolio Site (2 minutes)

### Test CloudFront

```bash
curl -I https://d1cda43lowke66.cloudfront.net

# Expected: HTTP/2 200
```

### Test Custom Domain (after SSL validates)

```bash
curl -I https://cv.vgnshlv.nz

# Expected: HTTP/2 200
```

### Browser Test

1. Open: https://cv.vgnshlv.nz
2. Verify:
   - ✅ Page loads (Unix man page theme)
   - ✅ Green padlock (SSL valid)
   - ✅ CV download button works
   - ✅ All images/CSS load
   - ✅ No console errors (F12)

---

## Step 7: Test Job Submission Form (2 minutes)

1. Open: https://cv.vgnshlv.nz/apply.html
2. Fill out test job:
   ```
   Job Title: Senior DevOps Engineer
   Company: Test Corp
   Your Name: Test Recruiter
   Email: test@example.com
   Salary Min: 8000
   Salary Max: 12000
   ```
3. Click **Submit Job Opportunity**
4. Expected: ✅ Success message with application ID

---

## Step 8: Set Up Cost Monitoring (5 minutes)

### Create Monthly Budget

1. Go to [AWS Budgets](https://console.aws.amazon.com/billing/home#/budgets)
2. Click **Create budget**
3. Select **Cost budget**
4. Configure:
   ```
   Budget name: JobTracker-Monthly
   Amount: $5.00
   Alerts: 50%, 80%, 100%
   Email: your-email@example.com
   ```
5. Click **Create budget**

### Enable Free Tier Alerts

1. Go to [Billing Preferences](https://console.aws.amazon.com/billing/home#/preferences)
2. Check **Receive Free Tier Usage Alerts**
3. Enter your email
4. Save

**Detailed instructions**: See COST-SETUP.md

---

## Step 9: Verify Everything Works (3 minutes)

### Run Post-Deployment Checklist

```bash
# CloudFront verification
./verify-cloudfront.sh

# Expected: All ✅ checks pass
```

### Manual Verification

- [ ] `https://cv.vgnshlv.nz` loads successfully
- [ ] SSL certificate valid (green padlock)
- [ ] Job submission form works
- [ ] API returns applications list
- [ ] Cost budgets configured
- [ ] Free tier alerts enabled

---

## Step 10: Clean Up Test Data (1 minute)

```bash
# Delete test application
APP_ID="app_2025-11-01_abc12345"  # From Step 4

curl -X DELETE "$API_BASE/applications/$APP_ID"

# Expected: {"application_id": "...", "deleted": true, "files_deleted": 2}
```

---

## 🎉 You're Live!

Your complete system is now operational:

✅ **Portfolio**: https://cv.vgnshlv.nz
✅ **Job Form**: https://cv.vgnshlv.nz/apply.html
✅ **API**: https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod
✅ **Cost Monitoring**: Active
✅ **Free Tier**: Optimized

---

## Next Steps

### Share Your Portfolio

Update these with your new URL:
- [ ] LinkedIn profile
- [ ] GitHub README
- [ ] Email signature
- [ ] Resume/CV documents
- [ ] Social media profiles

### Monitor Your System

**Daily** (automated):
- Cost anomaly alerts
- Free tier usage alerts

**Weekly**:
- Review CloudWatch Logs for errors
- Check application submissions

**Monthly**:
- Cost review (COST-SETUP.md)
- Performance optimization
- S3 storage cleanup

---

## Troubleshooting

### Issue: DNS not resolving

**Solution:**
```bash
# Check propagation
dig cv.vgnshlv.nz +short

# If empty, wait 5-15 more minutes
# DNS propagation can take up to 48 hours globally
```

### Issue: SSL certificate pending

**Solution:**
```bash
# Verify validation record exists
dig _09870b99f2b91d081db38b5ac73c4832.cv.vgnshlv.nz CNAME +short

# Should return: _ae18afce56fdbca76320361b0076a2e8.jkddzztszm.acm-validations.aws.

# Wait 5-30 minutes after DNS record added
```

### Issue: API returns 403/404

**Solution:**
```bash
# Check Lambda function deployed
aws lambda get-function \
  --function-name vgnshlvnz-job-tracker-api \
  --region ap-southeast-5

# If error, redeploy:
./deploy.sh job-tracker prod
```

### Issue: Form submission fails

**Solution:**
1. Open browser console (F12)
2. Check for CORS errors
3. Verify API endpoint in apply.html:
   ```javascript
   const API_BASE_URL = 'https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod';
   ```
4. Test API manually with curl (Step 4)

---

## Cost Estimates

**Month 1-12** (Free Tier): $0.00
**Month 13+**: ~$0.17 USD/month (~MYR 0.80)

**See detailed breakdown**: COST-SETUP.md

---

## Further Documentation

- **API Reference**: API.md
- **Cost Setup**: COST-SETUP.md
- **DNS Setup**: DNS-SETUP.md
- **Post-Deployment**: POST-DNS-CHECKLIST.md
- **Full Summary**: IMPLEMENTATION-SUMMARY.md

---

**Quick Start Version**: 1.0
**Last Updated**: November 1, 2025
**Estimated Time**: 30 minutes
**Difficulty**: Beginner-Intermediate
