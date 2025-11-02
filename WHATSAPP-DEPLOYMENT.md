# WhatsApp Notifications Deployment Guide

## Overview

This guide walks you through deploying WhatsApp notifications for your job tracker system.

**What's Implemented:**
- Python WhatsApp notification module (`whatsapp_notifier.py`)
- Integration with existing `POST /recruiter-submissions` endpoint
- Automatic notifications when recruiters submit job applications
- Graceful degradation (system works even if WhatsApp fails)

---

## Prerequisites

Before deploying, complete these steps:

1. **✅ Complete WhatsApp Business Account Setup**
   - Follow `WHATSAPP-SETUP.md` to get your credentials
   - You need:
     - `WHATSAPP_TOKEN` (permanent access token)
     - `PHONE_NUMBER_ID` (from Meta)
     - `RECIPIENT_NUMBER` (your WhatsApp number in E.164 format, e.g., `60123456789`)

2. **✅ Test WhatsApp API**
   - Send a test message using curl (see WHATSAPP-SETUP.md Step 5)
   - Verify you receive messages on your WhatsApp

---

## Step 1: Store Credentials in AWS Secrets Manager

### 1.1 Create Secret

```bash
# Replace with YOUR actual credentials
aws secretsmanager create-secret \
  --name job-tracker-whatsapp \
  --description "WhatsApp Business API credentials for job tracker notifications" \
  --secret-string '{
    "WHATSAPP_TOKEN": "EAAxxxxxxxxxxxxx",
    "PHONE_NUMBER_ID": "123456789012345",
    "BUSINESS_ACCOUNT_ID": "987654321098765",
    "RECIPIENT_NUMBER": "60123456789"
  }' \
  --region ap-southeast-5 \
  --tags Key=Project,Value=JobTracker Key=Environment,Value=prod

# Expected output:
# {
#     "ARN": "arn:aws:secretsmanager:ap-southeast-5:460742884565:secret:job-tracker-whatsapp-xxxxxx",
#     "Name": "job-tracker-whatsapp",
#     "VersionId": "..."
# }
```

### 1.2 Verify Secret

```bash
aws secretsmanager get-secret-value \
  --secret-id job-tracker-whatsapp \
  --region ap-southeast-5 \
  --query SecretString \
  --output text | jq '.'

# Should output your credentials (with actual values)
```

---

## Step 2: Update Lambda IAM Role

### 2.1 Get Current Role Name

```bash
aws lambda get-function \
  --function-name job-tracker-api \
  --region ap-southeast-5 \
  --query 'Configuration.Role' \
  --output text

# Output: arn:aws:iam::460742884565:role/JobTrackerLambdaRole
```

### 2.2 Create IAM Policy for Secrets Manager

```bash
# Create policy document
cat > /tmp/secrets-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:ap-southeast-5:460742884565:secret:job-tracker-whatsapp-*"
    }
  ]
}
EOF

# Create IAM policy
aws iam create-policy \
  --policy-name JobTrackerWhatsAppSecretsAccess \
  --policy-document file:///tmp/secrets-policy.json \
  --description "Allow job-tracker Lambda to read WhatsApp credentials from Secrets Manager"

# Output will include PolicyArn - save this!
# Example: arn:aws:iam::460742884565:policy/JobTrackerWhatsAppSecretsAccess
```

### 2.3 Attach Policy to Lambda Role

```bash
aws iam attach-role-policy \
  --role-name JobTrackerLambdaRole \
  --policy-arn arn:aws:iam::460742884565:policy/JobTrackerWhatsAppSecretsAccess

# No output means success
```

### 2.4 Verify Policy Attached

```bash
aws iam list-attached-role-policies \
  --role-name JobTrackerLambdaRole \
  --query 'AttachedPolicies[?contains(PolicyName, `WhatsApp`)]'

# Should show:
# [
#     {
#         "PolicyName": "JobTrackerWhatsAppSecretsAccess",
#         "PolicyArn": "arn:aws:iam::460742884565:policy/JobTrackerWhatsAppSecretsAccess"
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
cp src/whatsapp_notifier.py /tmp/lambda-deploy/

# Install dependencies (if any new ones needed)
if [ -f src/requirements.txt ]; then
  pip3 install -r src/requirements.txt -t /tmp/lambda-deploy/
fi

# Create deployment package
cd /tmp/lambda-deploy
zip -r /tmp/job-tracker-whatsapp.zip . > /dev/null

# Verify package size
ls -lh /tmp/job-tracker-whatsapp.zip
# Should be around 17-20 MB
```

### 3.2 Update Lambda Function

```bash
# Update function code
aws lambda update-function-code \
  --function-name job-tracker-api \
  --zip-file fileb:///tmp/job-tracker-whatsapp.zip \
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
# Check Lambda environment variables
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
#   "USER_POOL_ID": "ap-southeast-5_0QQg8Wd6r"
# }
```

---

## Step 4: Test WhatsApp Notifications

### 4.1 Test with Real Submission

```bash
# Submit a test job application
curl -X POST https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/recruiter-submissions \
  -H "Content-Type: application/json" \
  -d '{
    "recruiter": {
      "name": "Test Recruiter",
      "email": "test@example.com",
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

**Check WhatsApp on your phone** - you should receive:
```
🔔 *New Job Application Received*

*Recruiter Information:*
• Name: Test Recruiter
• Email: test@example.com
• Phone: +60-12-3456789
• Agency: Test Agency

*Job Details:*
• Title: Senior Python Developer
• Company: Tech Corp
• Salary: MYR 12,000 - 18,000
• Skills: Python, AWS, Lambda, API Gateway

*Requirements:*
5+ years Python experience, AWS knowledge required

_Submission ID: rec_2025-11-02_abc12345_
_Received: 2025-11-02T07:45:00Z_
```

### 4.2 Check Lambda Logs

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
# "WhatsApp credentials loaded successfully"
# "WhatsApp message sent successfully: wamid.xxx"
# "Sent text (wamid.xxx)"
```

### 4.3 Test Error Handling

**Test 1: Missing Credentials** (WhatsApp should gracefully degrade)
```bash
# Temporarily rename secret
aws secretsmanager update-secret \
  --secret-id job-tracker-whatsapp \
  --description "TEMPORARILY_DISABLED" \
  --region ap-southeast-5

# Submit another test application
# Response should have: "whatsapp_notification": "disabled"

# Re-enable
aws secretsmanager update-secret \
  --secret-id job-tracker-whatsapp \
  --description "WhatsApp Business API credentials for job tracker notifications" \
  --region ap-southeast-5
```

**Test 2: Invalid Token**
- Update secret with invalid token
- Submit application
- Check logs for "WhatsApp API error"
- Response should have: "whatsapp_notification": "failed"
- **Important:** Job submission should still succeed!

---

## Step 5: Monitor and Troubleshoot

### 5.1 CloudWatch Metrics

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

# Lambda errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=job-tracker-api \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region ap-southeast-5
```

### 5.2 Common Issues

**Issue 1: "whatsapp_notification": "disabled"**
- **Cause:** Credentials not found in Secrets Manager
- **Fix:** Verify secret exists and Lambda role has permission

```bash
# Check secret exists
aws secretsmanager describe-secret \
  --secret-id job-tracker-whatsapp \
  --region ap-southeast-5

# Check Lambda role permissions
aws iam get-role-policy \
  --role-name JobTrackerLambdaRole \
  --policy-name SecretsManagerAccess 2>/dev/null || echo "Policy not found"
```

**Issue 2: "whatsapp_notification": "failed"**
- **Cause:** WhatsApp API returned error
- **Fix:** Check CloudWatch logs for specific error

```bash
# Get detailed error
aws logs filter-log-events \
  --log-group-name /aws/lambda/job-tracker-api \
  --filter-pattern "WhatsApp API error" \
  --region ap-southeast-5 \
  --start-time $(date -u -d '30 minutes ago' +%s)000
```

Common WhatsApp API errors:
- `"code": 100, "message": "Invalid parameter"` → Check phone number format (E.164)
- `"code": 131047, "message": "Re-engagement message"` → 24-hour window expired, use template
- `"code": 131026, "message": "Message undeliverable"` → Recipient blocked you or doesn't have WhatsApp

**Issue 3: Messages not received**
- Verify recipient number is correct (E.164 format)
- Check test number restrictions (max 5 recipients)
- Verify recipient has WhatsApp installed
- Check WhatsApp Business Account status in Meta dashboard

---

## Step 6: Production Checklist

Before marking complete:

- [ ] WhatsApp Business Account fully verified
- [ ] Permanent access token generated and stored in Secrets Manager
- [ ] Lambda IAM role has Secrets Manager permissions
- [ ] Lambda code deployed with whatsapp_notifier.py
- [ ] Test message sent and received successfully
- [ ] Error handling tested (submission succeeds even if WhatsApp fails)
- [ ] CloudWatch logs show "WhatsApp message sent successfully"
- [ ] Monitoring and alerts configured

---

## Optional Enhancements

### Enhancement 1: Send CV with Notification

Currently, CV is uploaded AFTER the submission is created (via presigned URL). To include CV in WhatsApp:

**Option A: Trigger on S3 Upload**
- Add S3 event notification for CV uploads
- Trigger separate Lambda to send WhatsApp with CV
- Use existing file_validator Lambda

**Option B: Delayed Notification**
- Wait X seconds after submission
- Check if CV was uploaded
- Send WhatsApp with CV if available

### Enhancement 2: Template Messages

For production (outside 24-hour window), use approved templates:

```python
# In whatsapp_notifier.py, add:
def send_template_message(phone_number_id, token, recipient, template_name, parameters):
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
            "components": [{
                "type": "body",
                "parameters": [{"type": "text", "text": p} for p in parameters]
            }]
        }
    }
    return send_whatsapp_message(phone_number_id, token, recipient, payload)
```

### Enhancement 3: Two-Way Communication

Set up webhook to receive replies:

1. Configure webhook URL in Meta dashboard
2. Create API Gateway endpoint → Lambda
3. Process incoming messages (replies from you)
4. Update submission status based on replies

---

## Rollback Plan

If issues occur:

```bash
# 1. Redeploy previous Lambda version
PREV_VERSION=$(aws lambda list-versions-by-function \
  --function-name job-tracker-api \
  --region ap-southeast-5 \
  --query 'Versions[-2].Version' \
  --output text)

aws lambda update-function-code \
  --function-name job-tracker-api \
  --zip-file fileb:///tmp/old-lambda-package.zip \
  --region ap-southeast-5

# 2. Remove IAM policy (optional)
aws iam detach-role-policy \
  --role-name JobTrackerLambdaRole \
  --policy-arn arn:aws:iam::460742884565:policy/JobTrackerWhatsAppSecretsAccess

# 3. Delete secret (only if needed)
aws secretsmanager delete-secret \
  --secret-id job-tracker-whatsapp \
  --recovery-window-in-days 7 \
  --region ap-southeast-5
```

---

## Cost Estimate

**WhatsApp Cloud API Pricing:**
- User-initiated conversations: Free
- Business-initiated (templates): $0.005 - $0.03 per message (depending on country)
- Malaysia: ~$0.01 per business-initiated message

**Expected Monthly Cost:**
- Assuming 50 job applications/month
- All messages are user-initiated (within 24-hour window)
- **Cost: $0 USD/month**

**AWS Costs:**
- Secrets Manager: $0.40/month per secret
- Lambda: Negligible (within free tier)
- **Total additional cost: ~$0.40 USD/month**

---

## Support Resources

- **WhatsApp Cloud API Docs**: https://developers.facebook.com/docs/whatsapp/cloud-api
- **Meta Business Help**: https://www.facebook.com/business/help
- **AWS Secrets Manager**: https://docs.aws.amazon.com/secretsmanager/
- **CloudWatch Logs**: https://console.aws.amazon.com/cloudwatch/

---

## Next Steps

After successful deployment:

1. Update frontend to show WhatsApp notification status
2. Add admin dashboard feature to manually trigger WhatsApp for old submissions
3. Implement CV attachment in WhatsApp notifications
4. Set up message templates for business-initiated messages
5. Configure webhooks for two-way communication

---

**Deployment Date:** 2025-11-02
**Status:** 📋 READY FOR DEPLOYMENT
**Priority:** 🟢 FEATURE ENHANCEMENT

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
