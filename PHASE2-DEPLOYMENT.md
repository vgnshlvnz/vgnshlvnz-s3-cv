# Phase 2 Security Deployment Guide

## Summary of Phase 2 Enhancements

This deployment adds the remaining security features from the comprehensive security audit.

**Status:** Ready for deployment
**Priority:** HIGH - Completes security overhaul started in Phase 1

---

## What's New in Phase 2

### ✅ 1. File Upload Security
**File Validator Lambda Function** (`src/file_validator.py`)
- **Magic byte validation** - Verifies PDF (`%PDF-`), DOCX (`PK\x03\x04`), DOC file signatures
- **File size limits** - 10MB for CVs, 5MB for JDs
- **Suspicious pattern detection** - Scans for `<script>`, `javascript:`, `eval()`, etc.
- **PDF-specific checks** - Detects embedded JavaScript, validates EOF marker
- **DOCX macro detection** - Rejects files with VBA/macros
- **Auto-deletion** - Invalid files automatically removed from S3
- **S3 event trigger** - Runs on all file uploads to `applications/` prefix

### ✅ 2. API Gateway Cognito Authorizer
**JWT Authorization at Gateway Level** (template-job-tracker.yaml)
- **Default authorizer** - All routes require valid JWT token by default
- **Cognito integration** - Validates tokens against User Pool
- **Public endpoint override** - POST /applications explicitly allows anonymous access
- **Token validation** - Verifies issuer, audience, expiry at API Gateway level
- **Defense in depth** - Adds layer before Lambda validation

### ✅ 3. S3 CORS Tightening
**Stricter CORS Policy** (template-job-tracker.yaml)
- **Removed wildcards** - No more `'*'` in headers
- **Specific headers only** - Content-Type, Content-Length, Content-MD5, Authorization, etc.
- **Removed localhost** - Production bucket doesn't allow local development
- **Reduced methods** - Only GET and PUT (removed POST, HEAD)
- **Specific origins** - Only cv.vgnshlv.nz and CloudFront domain

### ✅ 4. CloudFront Security Headers
**Custom Response Headers Policy** (template-portfolio.yaml)
- **Content-Security-Policy (CSP)** - Strict policy for static site
  - `default-src 'self'`
  - Script/style sources whitelisted
  - `frame-ancestors 'none'` prevents clickjacking
- **Strict-Transport-Security (HSTS)** - Force HTTPS for 1 year, includeSubdomains, preload
- **X-Frame-Options: DENY** - Prevent iframe embedding
- **X-Content-Type-Options: nosniff** - Prevent MIME sniffing
- **X-XSS-Protection** - Browser XSS filter enabled
- **Referrer-Policy: strict-origin-when-cross-origin** - Control referrer information
- **Permissions-Policy** - Disable geolocation, microphone, camera, payment

---

## Files Modified

### New Files
1. **src/file_validator.py** (351 lines)
   - Complete file validation Lambda function
   - Magic byte checking, malware pattern detection
   - PDF/DOCX/DOC specific validation

2. **PHASE2-DEPLOYMENT.md** (this file)
   - Deployment guide for Phase 2 features

### Modified Files
1. **template-job-tracker.yaml**
   - Added FileValidatorFunction Lambda (lines 300-354)
   - Added S3 NotificationConfiguration (lines 139-170)
   - Added API Gateway JWT authorizer (lines 383-394)
   - Updated S3 CORS configuration (lines 111-131)
   - Added FileValidatorInvokePermission (lines 363-370)

2. **template-portfolio.yaml**
   - Added SecurityHeadersPolicy resource (lines 124-198)
   - Updated DefaultCacheBehavior to use custom policy (line 246)

---

## Deployment Steps

### Prerequisites
- Phase 1 security fixes deployed and working
- Cognito User Pool deployed (recruiter-portal-cognito stack)
- AWS CLI configured with ap-southeast-5 region

### Step 1: Deploy Job Tracker Updates

```bash
cd /home/agh0ri/vgnshlvnz-s3-bucket

# Build SAM application (packages Lambda code)
sam build --template template-job-tracker.yaml

# Deploy job tracker stack
sam deploy \
  --template-file template-job-tracker.yaml \
  --stack-name vgnshlvnz-job-tracker \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --parameter-overrides \
    BucketName=vgnshlvnz-job-tracker \
    Environment=prod \
    EnableDynamoDB=false \
    PresignedUrlExpiry=900 \
  --region ap-southeast-5 \
  --no-confirm-changeset

# Wait for stack to complete
aws cloudformation wait stack-update-complete \
  --stack-name vgnshlvnz-job-tracker \
  --region ap-southeast-5
```

### Step 2: Verify File Validator Lambda

```bash
# Check Lambda function was created
aws lambda get-function \
  --function-name vgnshlvnz-job-tracker-file-validator \
  --region ap-southeast-5

# Check S3 event notification is configured
aws s3api get-bucket-notification-configuration \
  --bucket vgnshlvnz-job-tracker

# Expected output: LambdaFunctionConfigurations with 3 entries (pdf, docx, doc)
```

### Step 3: Deploy Portfolio CloudFront Updates

```bash
# Deploy portfolio stack with security headers
sam deploy \
  --template-file template-portfolio.yaml \
  --stack-name vgnshlvnz-portfolio \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --parameter-overrides \
    BucketName=vgnshlvnz-portfolio \
    DomainName=cv.vgnshlv.nz \
    Environment=prod \
    CertificateArn=arn:aws:acm:us-east-1:460742884565:certificate/eca0af92-5e9e-4e06-a658-ca38bfa5b8c5 \
  --region ap-southeast-5 \
  --no-confirm-changeset

# Wait for stack update
aws cloudformation wait stack-update-complete \
  --stack-name vgnshlvnz-portfolio \
  --region ap-southeast-5

# Note: CloudFront distribution update takes 15-30 minutes to propagate globally
```

### Step 4: Verify CloudFront Security Headers

```bash
# Wait for CloudFront distribution to finish deploying
DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --stack-name vgnshlvnz-portfolio \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
  --output text)

aws cloudfront wait distribution-deployed \
  --id $DISTRIBUTION_ID

# Test security headers
curl -I https://cv.vgnshlv.nz

# Expected headers:
# - content-security-policy: default-src 'self'; ...
# - strict-transport-security: max-age=31536000; includeSubdomains; preload
# - x-frame-options: DENY
# - x-content-type-options: nosniff
# - x-xss-protection: 1; mode=block
# - referrer-policy: strict-origin-when-cross-origin
# - permissions-policy: geolocation=(), microphone=(), camera=(), payment=()
```

---

## Testing Phase 2 Features

### Test 1: File Validation - Valid PDF

```bash
# Upload a valid PDF to test file validator
echo "%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
%%EOF" > /tmp/test_valid.pdf

# Upload to S3 (should be accepted)
aws s3 cp /tmp/test_valid.pdf s3://vgnshlvnz-job-tracker/applications/test_rec_001/cv.pdf

# Check file still exists (not deleted)
aws s3 ls s3://vgnshlvnz-job-tracker/applications/test_rec_001/

# Check Lambda logs
aws logs tail /aws/lambda/vgnshlvnz-job-tracker-file-validator --follow
# Expected: "File validated successfully: applications/test_rec_001/cv.pdf"
```

### Test 2: File Validation - Invalid File (Fake PDF)

```bash
# Create a fake PDF (wrong magic bytes)
echo "This is not a PDF" > /tmp/test_invalid.pdf

# Upload to S3 (should be auto-deleted)
aws s3 cp /tmp/test_invalid.pdf s3://vgnshlvnz-job-tracker/applications/test_rec_002/cv.pdf

# Wait 5 seconds for Lambda to process
sleep 5

# Check file was deleted
aws s3 ls s3://vgnshlvnz-job-tracker/applications/test_rec_002/
# Expected: Empty (file deleted)

# Check Lambda logs
aws logs tail /aws/lambda/vgnshlvnz-job-tracker-file-validator --since 1m
# Expected: "Deleted invalid file ... Invalid PDF file signature"
```

### Test 3: File Validation - DOCX with Macros

```bash
# Create a test DOCX with macro content (simulated)
# Note: Full test requires actual DOCX file with vbaProject

# Check Lambda logs for macro detection
# Expected: "DOCX contains macros (not allowed for security)"
```

### Test 4: API Gateway JWT Authorizer

```bash
# Test unauthenticated request to protected endpoint (should fail)
curl -X GET https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications
# Expected: {"message":"Unauthorized"}

# Test public endpoint (should work without auth)
curl -X POST https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
# Expected: 200 OK or validation error (not 401 Unauthorized)

# Test with valid JWT token
# (Get token from Cognito login first)
TOKEN="<your-jwt-token>"
curl -X GET https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with data
```

### Test 5: S3 CORS Restrictions

```bash
# Test CORS from browser console on cv.vgnshlv.nz
# Should work:
fetch('https://vgnshlvnz-job-tracker.s3.ap-southeast-5.amazonaws.com/test.pdf', {
  method: 'GET',
  headers: { 'Content-Type': 'application/pdf' }
})

# Should fail (localhost origin):
# Open http://localhost:3000 and try same fetch
# Expected: CORS error
```

### Test 6: CloudFront Security Headers

```bash
# Test CSP header
curl -I https://cv.vgnshlv.nz | grep -i content-security-policy
# Expected: content-security-policy: default-src 'self'; script-src 'self' 'unsafe-inline' ...

# Test HSTS
curl -I https://cv.vgnshlv.nz | grep -i strict-transport-security
# Expected: strict-transport-security: max-age=31536000; includeSubdomains; preload

# Test X-Frame-Options
curl -I https://cv.vgnshlv.nz | grep -i x-frame-options
# Expected: x-frame-options: DENY

# Use online security scanner
# https://securityheaders.com/?q=https://cv.vgnshlv.nz
# Expected: A or A+ rating
```

---

## Security Testing Checklist

### File Upload Security
- [ ] Valid PDF files accepted
- [ ] Invalid PDF signatures rejected and deleted
- [ ] Valid DOCX files accepted
- [ ] DOCX files with macros rejected
- [ ] Files over size limit rejected (10MB CV, 5MB JD)
- [ ] Suspicious patterns detected (script tags, eval, etc.)
- [ ] Lambda logs show validation results
- [ ] S3 tags applied to validated files

### API Gateway Authorization
- [ ] Unauthenticated requests to GET endpoints return 401
- [ ] Public POST endpoint works without token
- [ ] Valid JWT tokens grant access
- [ ] Expired/invalid tokens rejected
- [ ] API Gateway logs show authorization decisions

### S3 CORS
- [ ] Requests from cv.vgnshlv.nz allowed
- [ ] Requests from CloudFront domain allowed
- [ ] Requests from localhost blocked (in production)
- [ ] Only allowed headers accepted
- [ ] Only GET and PUT methods work

### CloudFront Security Headers
- [ ] CSP header present and correct
- [ ] HSTS header enforces HTTPS
- [ ] X-Frame-Options prevents embedding
- [ ] X-Content-Type-Options prevents MIME sniffing
- [ ] X-XSS-Protection enabled
- [ ] Referrer-Policy set correctly
- [ ] Permissions-Policy disables dangerous features
- [ ] SecurityHeaders.com gives A/A+ rating

---

## Rollback Plan

If issues occur, rollback to previous stack versions:

```bash
# Rollback job tracker stack
aws cloudformation cancel-update-stack \
  --stack-name vgnshlvnz-job-tracker \
  --region ap-southeast-5

# Or deploy previous template version
sam deploy \
  --template-file template-job-tracker.yaml.backup \
  --stack-name vgnshlvnz-job-tracker \
  --no-confirm-changeset

# Rollback portfolio stack
aws cloudformation cancel-update-stack \
  --stack-name vgnshlvnz-portfolio \
  --region ap-southeast-5
```

---

## Monitoring After Deployment

### CloudWatch Metrics

```bash
# Monitor file validator Lambda errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=vgnshlvnz-job-tracker-file-validator \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Monitor file validator invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=vgnshlvnz-job-tracker-file-validator \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### Lambda Logs

```bash
# View file validator logs
aws logs tail /aws/lambda/vgnshlvnz-job-tracker-file-validator --follow

# Search for validation failures
aws logs filter-log-events \
  --log-group-name /aws/lambda/vgnshlvnz-job-tracker-file-validator \
  --filter-pattern "REJECTED"

# Search for deleted files
aws logs filter-log-events \
  --log-group-name /aws/lambda/vgnshlvnz-job-tracker-file-validator \
  --filter-pattern "Deleted invalid file"
```

---

## Cost Impact

**Expected increase:** $0.50 - $2.00 USD/month

### Breakdown
- **File Validator Lambda:** $0 (within free tier for low usage)
  - Free tier: 1M requests/month, 400,000 GB-seconds
  - Expected: <1000 invocations/month
- **API Gateway JWT Authorizer:** $0 (no extra cost for authorizers)
- **CloudFront Custom Headers Policy:** $0 (no extra cost for custom policies)
- **S3 Event Notifications:** $0 (free)

### Optimization Tips
- File validator only runs on file uploads (not on every API call)
- JWT validation at API Gateway reduces Lambda cold starts
- CloudFront caching reduces origin requests

---

## Known Limitations

1. **File Validator is Basic**
   - No actual malware scanning (ClamAV not integrated)
   - Pattern matching only detects common threats
   - For production, consider AWS GuardDuty or third-party scanners

2. **API Gateway Authorizer Cache**
   - JWT tokens cached for 5 minutes by default
   - Token revocation may take up to 5 minutes to propagate
   - Can disable cache with `AuthorizerResultTtlInSeconds: 0`

3. **S3 CORS Still Allows CloudFront**
   - CloudFront domain is still in allowed origins
   - Consider removing for stricter security
   - May break some legitimate use cases

4. **CSP Policy May Be Too Strict**
   - `'unsafe-inline'` allowed for scripts/styles
   - May need adjustment based on actual site requirements
   - Test thoroughly in staging before production

---

## Next Steps (Phase 3 - Optional)

After Phase 2 is deployed and stable:

1. **Integrate ClamAV** for real malware scanning
2. **Add DynamoDB rate limiting** (replace in-memory)
3. **Enable AWS GuardDuty** for threat detection
4. **Add CloudWatch alarms** for validation failures
5. **Implement automated security scanning** in CI/CD
6. **Add WAF rules** for API Gateway (DDoS protection)
7. **Enable CloudTrail** for audit logging

---

## Troubleshooting

### Issue: File Validator Not Triggering

**Symptoms:** Files uploaded but Lambda not invoked

**Checks:**
1. Verify S3 event notification configured: `aws s3api get-bucket-notification-configuration --bucket vgnshlvnz-job-tracker`
2. Check Lambda permissions: Lambda should have `s3:GetObject`, `s3:DeleteObject`
3. Check CloudWatch Logs: `aws logs tail /aws/lambda/vgnshlvnz-job-tracker-file-validator`

**Fix:**
```bash
# Manually add Lambda permission if missing
aws lambda add-permission \
  --function-name vgnshlvnz-job-tracker-file-validator \
  --statement-id AllowS3Invoke \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::vgnshlvnz-job-tracker
```

### Issue: API Gateway Returns 401 for Public Endpoint

**Symptoms:** POST /applications returns Unauthorized

**Checks:**
1. Verify event has `Auth: Authorizer: NONE` override
2. Check API Gateway route configuration

**Fix:** Redeploy stack or manually set authorizer to NONE for that route in console.

### Issue: CloudFront Headers Not Appearing

**Symptoms:** Security headers missing in curl output

**Checks:**
1. Verify distribution finished deploying: `aws cloudfront wait distribution-deployed --id <id>`
2. Check ResponseHeadersPolicy attached: `aws cloudfront get-distribution-config --id <id>`
3. Clear browser cache and test with curl

**Fix:** Wait for distribution to deploy (can take 30 minutes), then invalidate cache.

---

**Deployment Date:** 2025-11-02
**Phase:** 2 of 2 (Security Overhaul Complete)
**Status:** ✅ READY FOR DEPLOYMENT
**Priority:** 🟡 HIGH - Completes comprehensive security audit fixes

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
