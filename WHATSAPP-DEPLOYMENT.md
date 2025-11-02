# WhatsApp Notifications Deployment Guide (Amazon Pinpoint)

## Overview

This guide walks you through deploying WhatsApp notifications using Amazon Pinpoint for your job tracker system.

**What's Implemented:**
- Python Pinpoint WhatsApp module (`whatsapp_pinpoint.py`)
- Automatic notifications when recruiters submit job applications
- Manual trigger endpoint for admin (`POST /recruiter-submissions/{id}/send-whatsapp`)
- WhatsApp notification history tracking
- Admin dashboard with WhatsApp buttons
- Graceful degradation (system works even if WhatsApp fails)

**Why Amazon Pinpoint?**
- AWS-native solution (no external API tokens)
- Integrated monitoring with CloudWatch
- Built-in analytics and delivery tracking
- IAM-based authentication
- Part of existing AWS infrastructure

---

## Prerequisites

Before deploying, complete these steps:

1. **✅ Complete Pinpoint Setup**
   - Follow `PINPOINT-SETUP.md` to configure Amazon Pinpoint
   - You need:
     - `PINPOINT_APP_ID` (from Pinpoint project)
     - `PINPOINT_ORIGINATION_NUMBER` (WhatsApp-enabled phone number)
     - `PINPOINT_RECIPIENT_NUMBER` (your WhatsApp number in E.164 format)

2. **✅ Verify Pinpoint Configuration**
   - Send test message using AWS CLI (see PINPOINT-SETUP.md Step 6)
   - Verify you receive messages on your WhatsApp
   - Confirm IAM permissions are set up

---

## Step 1: Configure Lambda Environment Variables

### 1.1 Set Environment Variables

```bash
# Get current configuration
aws lambda get-function-configuration \
  --function-name job-tracker-api \
  --region ap-southeast-5 \
  --query 'Environment.Variables' > /tmp/current-env.json

# Add Pinpoint variables (update with YOUR values)
aws lambda update-function-configuration \
  --function-name job-tracker-api \
  --environment Variables="{
    BUCKET_NAME=vgnshlvnz-job-tracker,
    CLIENT_ID=4f8f3qon7v6tegud4qe854epo6,
    USER_POOL_ID=ap-southeast-5_0QQg8Wd6r,
    REGION=ap-southeast-5,
    PRESIGNED_URL_EXPIRY=900,
    PINPOINT_APP_ID=YOUR_PINPOINT_APP_ID,
    PINPOINT_ORIGINATION_NUMBER=+60123456789,
    PINPOINT_RECIPIENT_NUMBER=+60987654321
  }" \
  --region ap-southeast-5

# Expected output includes the three PINPOINT_* variables
```

### 1.2 Verify Configuration

```bash
aws lambda get-function-configuration \
  --function-name job-tracker-api \
  --region ap-southeast-5 \
  --query 'Environment.Variables' | jq '.'

# Should include:
# {
#   "BUCKET_NAME": "vgnshlvnz-job-tracker",
#   "CLIENT_ID": "4f8f3qon7v6tegud4qe854epo6",
#   "PRESIGNED_URL_EXPIRY": "900",
#   "REGION": "ap-southeast-5",
#   "USER_POOL_ID": "ap-southeast-5_0QQg8Wd6r",
#   "PINPOINT_APP_ID": "abc123def456",
#   "PINPOINT_ORIGINATION_NUMBER": "+60123456789",
#   "PINPOINT_RECIPIENT_NUMBER": "+60987654321"
# }
```

---

## Step 2: Update Lambda IAM Role

### 2.1 Create Pinpoint Access Policy

```bash
# Create policy document
cat > /tmp/pinpoint-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mobiletargeting:SendMessages",
        "mobiletargeting:SendUsersMessages",
        "mobiletargeting:GetEndpoint",
        "mobiletargeting:UpdateEndpoint"
      ],
      "Resource": "arn:aws:mobiletargeting:ap-southeast-5:460742884565:apps/*"
    }
  ]
}
EOF

# Create IAM policy
aws iam create-policy \
  --policy-name JobTrackerPinpointAccess \
  --policy-document file:///tmp/pinpoint-policy.json \
  --description "Allow job-tracker Lambda to send WhatsApp via Amazon Pinpoint"

# Output will include PolicyArn - save this!
# Example: arn:aws:iam::460742884565:policy/JobTrackerPinpointAccess
```

### 2.2 Attach Policy to Lambda Role

```bash
aws iam attach-role-policy \
  --role-name JobTrackerLambdaRole \
  --policy-arn arn:aws:iam::460742884565:policy/JobTrackerPinpointAccess

# No output means success
```

### 2.3 Verify Policy Attached

```bash
aws iam list-attached-role-policies \
  --role-name JobTrackerLambdaRole \
  --query 'AttachedPolicies[?contains(PolicyName, `Pinpoint`)]'

# Should show:
# [
#     {
#         "PolicyName": "JobTrackerPinpointAccess",
#         "PolicyArn": "arn:aws:iam::460742884565:policy/JobTrackerPinpointAccess"
#     }
# ]
```

---

## Step 3: Deploy Updated Lambda Code

### 3.1 Package Lambda Function

```bash
cd /home/agh0ri/vgnshlvnz-s3-bucket

# Create clean package directory
rm -rf /tmp/lambda-deploy
mkdir -p /tmp/lambda-deploy

# Copy Lambda code
cp src/app.py /tmp/lambda-deploy/
cp src/whatsapp_pinpoint.py /tmp/lambda-deploy/

# Install dependencies (if any new ones needed)
if [ -f src/requirements.txt ]; then
  pip3 install -r src/requirements.txt -t /tmp/lambda-deploy/
fi

# Create deployment package
cd /tmp/lambda-deploy
zip -r /tmp/job-tracker-pinpoint.zip . > /dev/null

# Verify package size
ls -lh /tmp/job-tracker-pinpoint.zip
# Should be around 17-20 MB (or less without external dependencies)
```

### 3.2 Update Lambda Function

```bash
# Update function code
aws lambda update-function-code \
  --function-name job-tracker-api \
  --zip-file fileb:///tmp/job-tracker-pinpoint.zip \
  --region ap-southeast-5 \
  --output json | jq '.FunctionName, .Runtime, .LastModified, .CodeSize'

# Output:
# "job-tracker-api"
# "python3.12"
# "2025-11-02T..."
# 18234567
```

### 3.3 Wait for Update to Complete

```bash
aws lambda wait function-updated \
  --function-name job-tracker-api \
  --region ap-southeast-5

echo "Lambda update complete!"
```

### 3.4 Verify Deployment

```bash
# Check Lambda configuration
aws lambda get-function-configuration \
  --function-name job-tracker-api \
  --region ap-southeast-5 \
  --query '{Runtime: Runtime, LastModified: LastModified, CodeSize: CodeSize, Environment: Environment.Variables}' \
  | jq '.'

# Verify all PINPOINT_* environment variables are present
```

---

## Step 4: Deploy Updated Dashboard

### 4.1 Upload Updated HTML to S3

```bash
# Upload updated recruiter dashboard with WhatsApp buttons
aws s3 cp recruiter-dashboard.html \
  s3://vgnshlvnz-portfolio/ \
  --content-type text/html \
  --region ap-southeast-5

# Verify upload
aws s3 ls s3://vgnshlvnz-portfolio/recruiter-dashboard.html
```

### 4.2 Invalidate CloudFront Cache

```bash
# Get CloudFront distribution ID
DIST_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?contains(Aliases.Items, 'cv.vgnshlv.nz')].Id" \
  --output text)

# Create invalidation for dashboard
aws cloudfront create-invalidation \
  --distribution-id $DIST_ID \
  --paths "/recruiter-dashboard.html"

# Wait for invalidation to complete (usually 1-5 minutes)
```

### 4.3 Verify Dashboard Update

```bash
# Download from CloudFront to verify
curl -s https://cv.vgnshlv.nz/recruiter-dashboard.html | grep -o "sendWhatsApp"

# Should output: "sendWhatsApp" (multiple times)
```

---

## Step 5: Test WhatsApp Notifications

### 5.1 Test Automatic Notification

Submit a test job application:

```bash
curl -X POST https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/recruiter-submissions \
  -H "Content-Type: application/json" \
  -d '{
    "recruiter": {
      "name": "Test Recruiter - Auto",
      "email": "test-auto@example.com",
      "phone": "+60-12-3456789",
      "agency": "Test Agency"
    },
    "job": {
      "title": "Senior Python Developer",
      "company": "Tech Corp",
      "salary_min": 12000,
      "salary_max": 18000,
      "currency": "MYR",
      "requirements": "5+ years Python experience, AWS knowledge required",
      "skills": ["Python", "AWS", "Lambda", "API Gateway"],
      "description": "Exciting role working on serverless applications"
    }
  }'
```

**Expected Response:**
```json
{
  "submission_id": "rec_2025-11-02_abc12345",
  "jd_upload_url": "https://...",
  "jd_upload_url_expires_in": 600,
  "created_at": "2025-11-02T07:45:00Z",
  "whatsapp_notification": "sent"
}
```

**Check your WhatsApp** - you should receive:
```
🔔 New Job Application

👤 Test Recruiter - Auto
📧 test-auto@example.com
📞 +60-12-3456789
🏢 Test Agency

💼 Senior Python Developer at Tech Corp
💰 MYR 12,000 - 18,000
🔧 Python, AWS, Lambda, API Gateway

📋 rec_2025-11-02_abc12345
```

### 5.2 Test Manual Trigger

First, get an access token from the admin dashboard by logging in, then:

```bash
# Login first to get token (use recruiter-dashboard.html)
# Copy JWT token from browser console after login

TOKEN="YOUR_JWT_TOKEN_HERE"
SUBMISSION_ID="rec_2025-11-02_abc12345"

# Manually trigger WhatsApp
curl -X POST "https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/recruiter-submissions/$SUBMISSION_ID/send-whatsapp" \
  -H "Authorization: Bearer $TOKEN"

# Expected response:
# {
#   "submission_id": "rec_2025-11-02_abc12345",
#   "status": "sent",
#   "message_id": "msg-xyz789",
#   "sent_at": "2025-11-02T08:00:00Z",
#   "sent_by": "admin@vgnshlv.nz"
# }
```

### 5.3 Test Dashboard UI

1. **Login** to https://cv.vgnshlv.nz/recruiter-dashboard.html
2. **Check table** - each submission should have 💬 button
3. **Click WhatsApp button** in table row - confirm dialog appears
4. **View submission details** - should show "WhatsApp Notifications" section
5. **Check history** - automatic send should be listed
6. **Click "Send WhatsApp Now"** - should trigger manual send
7. **Refresh details** - manual send should appear in history

### 5.4 Check Lambda Logs

```bash
# View recent logs
aws logs tail /aws/lambda/job-tracker-api --follow --region ap-southeast-5

# Search for WhatsApp-related logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/job-tracker-api \
  --filter-pattern "WhatsApp" \
  --region ap-southeast-5 \
  --start-time $(date -u -d '10 minutes ago' +%s)000

# Look for:
# "WhatsApp notification sent via Pinpoint: msg-abc123"
# "Pinpoint message sent successfully: msg-abc123"
# "Manual WhatsApp notification sent for rec_xxx"
```

### 5.5 Check Pinpoint Analytics

```bash
# Get delivery metrics (may take a few minutes to appear)
aws pinpoint get-application-date-range-kpi \
  --application-id YOUR_PINPOINT_APP_ID \
  --kpi-name messages-sent \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)Z \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S)Z \
  --region ap-southeast-5

# Via Console: Pinpoint → Analytics → Overview
```

---

## Step 6: Monitor and Troubleshoot

### 6.1 CloudWatch Metrics

```bash
# Lambda invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=job-tracker-api \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region ap-southeast-5

# Pinpoint delivery rate
aws cloudwatch get-metric-statistics \
  --namespace AWS/Pinpoint \
  --metric-name DeliveryRate \
  --dimensions Name=ApplicationId,Value=YOUR_PINPOINT_APP_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region ap-southeast-5
```

### 6.2 Common Issues

**Issue 1: "whatsapp_notification": "disabled"**
- **Cause:** Pinpoint environment variables not set
- **Fix:** Verify Lambda environment variables (Step 1.2)

**Issue 2: "whatsapp_notification": "failed"**
- **Cause:** Pinpoint API returned error
- **Fix:** Check CloudWatch logs for specific error

```bash
# Get detailed error
aws logs filter-log-events \
  --log-group-name /aws/lambda/job-tracker-api \
  --filter-pattern "Pinpoint" \
  --region ap-southeast-5 \
  --start-time $(date -u -d '30 minutes ago' +%s)000
```

Common Pinpoint errors:
- **Invalid phone number format** → Use E.164 format (+60123456789)
- **Permission denied** → Check IAM policy attached (Step 2.3)
- **Application not found** → Verify PINPOINT_APP_ID is correct
- **Origination number invalid** → Verify number provisioned in Pinpoint

**Issue 3: Messages not received**
- Verify recipient number is correct (E.164 format)
- Check recipient has WhatsApp installed
- Verify origination number is WhatsApp-enabled
- Check Pinpoint console for delivery status

**Issue 4: Manual trigger returns 401**
- Admin not logged in
- JWT token expired (refresh login)
- Token not passed in Authorization header

**Issue 5: Manual trigger returns 403**
- User is not admin
- Check Cognito user groups
- Verify admin attribute in JWT

---

## Step 7: Production Checklist

Before marking complete:

- [ ] Amazon Pinpoint project created
- [ ] WhatsApp-enabled phone number provisioned
- [ ] Environment variables configured in Lambda
- [ ] IAM policy attached to Lambda role
- [ ] Lambda code deployed with whatsapp_pinpoint.py
- [ ] Dashboard updated with WhatsApp buttons
- [ ] Automatic notification tested (submission → WhatsApp)
- [ ] Manual trigger tested (dashboard button → WhatsApp)
- [ ] WhatsApp history displays correctly in dashboard
- [ ] CloudWatch logs show successful deliveries
- [ ] Pinpoint analytics show message counts
- [ ] Error handling tested (graceful degradation works)
- [ ] Monitoring and alerts configured

---

## Optional Enhancements

### Enhancement 1: Message Templates

For re-engagement messages outside 24-hour window:

```bash
# Create template in Pinpoint console
# Template name: job_application_reminder
# Content: Pre-approved message for follow-ups

# Use template in code (update whatsapp_pinpoint.py):
# Use send_template_message() function instead of send_whatsapp_message()
```

### Enhancement 2: Two-Way Messaging

Set up webhook to receive WhatsApp replies:

1. Create new Lambda for webhook processing
2. Configure API Gateway endpoint
3. Register webhook URL in Pinpoint
4. Process incoming messages (status updates from admin)

### Enhancement 3: Bulk Notifications

Add bulk send capability to dashboard:

```javascript
// In recruiter-dashboard.html
async function sendBulkWhatsApp(submissionIds) {
  for (const id of submissionIds) {
    await sendWhatsApp(id);
    await new Promise(r => setTimeout(r, 2000)); // Rate limiting
  }
}
```

### Enhancement 4: Rich Media

Send custom CV with WhatsApp notification (requires Pinpoint MMS):

```python
# In whatsapp_pinpoint.py - extend send_application_notification()
# to include document/image attachments
```

---

## Rollback Plan

If issues occur:

```bash
# 1. Redeploy previous Lambda version
aws lambda list-versions-by-function \
  --function-name job-tracker-api \
  --region ap-southeast-5 \
  --query 'Versions[-2].Version'

# 2. Update to previous version
aws lambda update-function-code \
  --function-name job-tracker-api \
  --zip-file fileb:///tmp/old-lambda-package.zip \
  --region ap-southeast-5

# 3. Remove Pinpoint environment variables (optional)
aws lambda update-function-configuration \
  --function-name job-tracker-api \
  --environment Variables="{
    BUCKET_NAME=vgnshlvnz-job-tracker,
    CLIENT_ID=4f8f3qon7v6tegud4qe854epo6,
    USER_POOL_ID=ap-southeast-5_0QQg8Wd6r,
    REGION=ap-southeast-5,
    PRESIGNED_URL_EXPIRY=900
  }" \
  --region ap-southeast-5

# 4. Detach IAM policy (optional)
aws iam detach-role-policy \
  --role-name JobTrackerLambdaRole \
  --policy-arn arn:aws:iam::460742884565:policy/JobTrackerPinpointAccess
```

---

## Cost Estimate

**Amazon Pinpoint WhatsApp Pricing:**
- User-initiated messages (within 24-hour window): **Free**
- Business-initiated (templates, outside window):
  - Malaysia: ~$0.01 USD per message
  - US: ~$0.02 USD per message

**Expected Monthly Cost:**
- Assuming 50 job applications/month
- All automatic notifications (user-initiated, within 24-hour window)
- **WhatsApp Cost: $0 USD/month**

**AWS Infrastructure Costs:**
- Lambda: Negligible (within free tier)
- Pinpoint: $0 (free tier includes 5,000 targeted messages/month)
- CloudWatch: ~$0.50 USD/month (logs and metrics)
- **Total: ~$0.50 USD/month**

**Note:** Manual notifications sent days later may incur charges if using templates.

---

## Support Resources

- **Amazon Pinpoint Docs**: https://docs.aws.amazon.com/pinpoint/
- **SMS/WhatsApp Channel**: https://docs.aws.amazon.com/pinpoint/latest/userguide/channels-sms.html
- **CloudWatch Monitoring**: https://docs.aws.amazon.com/pinpoint/latest/userguide/monitoring-cloudwatch.html
- **Message Templates**: https://docs.aws.amazon.com/pinpoint/latest/userguide/message-templates.html
- **IAM Permissions**: https://docs.aws.amazon.com/pinpoint/latest/developerguide/permissions-actions.html

---

## Next Steps

After successful deployment:

1. Monitor delivery rates in Pinpoint console
2. Set up CloudWatch alarms for failures
3. Create additional message templates for different scenarios
4. Consider implementing two-way messaging
5. Add rich media support (images, documents)
6. Optimize message content based on analytics

---

**Deployment Date:** 2025-11-02
**Status:** 📋 READY FOR DEPLOYMENT
**Priority:** 🟢 FEATURE ENHANCEMENT
**Integration:** Amazon Pinpoint (AWS-native)

Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
