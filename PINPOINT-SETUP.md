# Amazon Pinpoint WhatsApp Setup Guide

## Overview

This guide walks you through setting up Amazon Pinpoint for WhatsApp notifications in your job tracker system.

**What is Amazon Pinpoint?**
- AWS-native messaging service supporting SMS, email, push, and WhatsApp
- Built-in analytics and delivery tracking
- No need for external Meta Business Account integration
- Uses AWS IAM for authentication (no separate access tokens)

**Advantages vs Direct Meta Cloud API:**
- Fully managed by AWS (no external token management)
- Integrated with CloudWatch for monitoring
- Built-in delivery analytics and metrics
- Simpler IAM-based authentication
- Part of your existing AWS infrastructure

---

## Prerequisites

Before starting:

1. **AWS Account** with appropriate permissions
2. **Phone number** for WhatsApp Business (will be provisioned through AWS)
3. **Business verification** (required for production WhatsApp access)
4. **Admin access** to AWS Console and CLI

---

## Step 1: Enable Amazon Pinpoint

### 1.1 Create Pinpoint Project

```bash
# Create Pinpoint application
aws pinpoint create-app \
  --create-application-request Name=JobTrackerWhatsApp \
  --region ap-southeast-5

# Save the ApplicationId from response (you'll need this)
# Example output:
# {
#     "ApplicationResponse": {
#         "Id": "abc123def456",
#         "Arn": "arn:aws:mobiletargeting:ap-southeast-5:460742884565:apps/abc123def456",
#         "Name": "JobTrackerWhatsApp"
#     }
# }
```

**Via AWS Console:**
1. Go to **Amazon Pinpoint** console: https://console.aws.amazon.com/pinpoint/
2. Click **Create a project**
3. Project name: `JobTrackerWhatsApp`
4. Features: Select **Campaigns** and **Messaging**
5. Click **Create**
6. Note the **Project ID** (application ID)

### 1.2 Verify Pinpoint Project

```bash
# List Pinpoint applications
aws pinpoint get-apps --region ap-southeast-5

# Get specific app details
aws pinpoint get-app \
  --application-id YOUR_APP_ID \
  --region ap-southeast-5
```

---

## Step 2: Request WhatsApp Business Number

Amazon Pinpoint provides WhatsApp-enabled phone numbers through AWS End User Messaging.

### 2.1 Request Number via AWS Console

1. Go to **Amazon Pinpoint** → Your project → **SMS and voice**
2. Navigate to **Phone numbers** → **Request phone number**
3. Select:
   - **Country**: Malaysia (or your region)
   - **Number type**: Toll-free or Long code
   - **SMS/MMS**: Enabled
   - **WhatsApp**: ✅ **Enable WhatsApp Business**
4. Review pricing and click **Request**

**Important Notes:**
- WhatsApp-enabled numbers may have limited availability
- Additional verification may be required
- Processing time: 1-5 business days
- Alternative: Use existing Meta WhatsApp Business number (requires linking)

### 2.2 Link Existing WhatsApp Business Number (Alternative)

If you already have a WhatsApp Business number through Meta:

```bash
# This feature is in preview - check AWS documentation
# You'll need your:
# - WhatsApp Business Account ID (from Meta)
# - Phone Number ID
# - API credentials from Meta
```

**Via Console:**
1. Pinpoint → **SMS and voice** → **WhatsApp**
2. Click **Link existing WhatsApp Business account**
3. Follow Meta authentication flow
4. Grant Pinpoint permissions to send messages

---

## Step 3: Configure WhatsApp Channel

### 3.1 Enable WhatsApp in Pinpoint

```bash
# Enable WhatsApp channel (after number provisioning)
# Note: This uses SMS channel with WhatsApp capabilities

# Update SMS settings
aws pinpoint update-sms-channel \
  --application-id YOUR_APP_ID \
  --sms-channel-request Enabled=true \
  --region ap-southeast-5
```

### 3.2 Set Origination Number

```bash
# Get your provisioned phone number
aws pinpoint get-phone-numbers \
  --region ap-southeast-5

# Example output:
# {
#     "PhoneNumbers": [{
#         "PhoneNumber": "+60123456789",
#         "NumberType": "LONG_CODE",
#         "Capabilities": ["SMS", "VOICE", "WHATSAPP"]
#     }]
# }
```

Save this phone number - it will be your `PINPOINT_ORIGINATION_NUMBER`.

### 3.3 Configure Message Templates (Optional)

For production use outside 24-hour conversation windows, create approved templates:

**Via Console:**
1. Pinpoint → **Message templates** → **Create template**
2. Template name: `job_application_notification`
3. Template type: **SMS** (will work for WhatsApp)
4. Message content:
   ```
   🔔 New Job Application

   👤 {{recruiter_name}}
   📧 {{recruiter_email}}

   💼 {{job_title}} at {{company}}
   💰 {{salary_range}}

   📋 {{submission_id}}
   ```
5. Submit for approval (if using WhatsApp)

**Template Approval:**
- Required for WhatsApp messages outside 24-hour window
- Approval time: 1-2 hours
- WhatsApp template policies apply
- SMS templates don't require approval

---

## Step 4: Configure Lambda Environment Variables

Update your Lambda function with Pinpoint configuration:

### 4.1 Set Environment Variables

```bash
# Update Lambda environment variables
aws lambda update-function-configuration \
  --function-name job-tracker-api \
  --environment Variables="{
    BUCKET_NAME=vgnshlvnz-job-tracker,
    CLIENT_ID=4f8f3qon7v6tegud4qe854epo6,
    USER_POOL_ID=ap-southeast-5_0QQg8Wd6r,
    REGION=ap-southeast-5,
    PRESIGNED_URL_EXPIRY=900,
    PINPOINT_APP_ID=YOUR_APP_ID,
    PINPOINT_ORIGINATION_NUMBER=+60123456789,
    PINPOINT_RECIPIENT_NUMBER=+60987654321
  }" \
  --region ap-southeast-5

# Wait for update to complete
aws lambda wait function-updated \
  --function-name job-tracker-api \
  --region ap-southeast-5
```

**Environment Variables Explained:**

| Variable | Example | Description |
|----------|---------|-------------|
| `PINPOINT_APP_ID` | `abc123def456` | Pinpoint application ID from Step 1 |
| `PINPOINT_ORIGINATION_NUMBER` | `+60123456789` | WhatsApp-enabled phone from Step 2 |
| `PINPOINT_RECIPIENT_NUMBER` | `+60987654321` | Your WhatsApp number (E.164 format) |

**E.164 Phone Number Format:**
- Country code + number
- No spaces, dashes, or parentheses
- Examples:
  - Malaysia: `+60123456789`
  - US: `+14155551234`
  - Singapore: `+6598765432`

### 4.2 Verify Configuration

```bash
# Check environment variables
aws lambda get-function-configuration \
  --function-name job-tracker-api \
  --region ap-southeast-5 \
  --query 'Environment.Variables' | jq '.'

# Should show all three PINPOINT_* variables
```

---

## Step 5: Update Lambda IAM Permissions

Grant Lambda permission to use Pinpoint:

### 5.1 Create Pinpoint Policy

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
  --description "Allow job-tracker Lambda to send WhatsApp via Pinpoint"

# Save the PolicyArn from output
# Example: arn:aws:iam::460742884565:policy/JobTrackerPinpointAccess
```

### 5.2 Attach Policy to Lambda Role

```bash
# Get Lambda execution role
aws lambda get-function \
  --function-name job-tracker-api \
  --region ap-southeast-5 \
  --query 'Configuration.Role' \
  --output text

# Output: arn:aws:iam::460742884565:role/JobTrackerLambdaRole

# Attach Pinpoint policy
aws iam attach-role-policy \
  --role-name JobTrackerLambdaRole \
  --policy-arn arn:aws:iam::460742884565:policy/JobTrackerPinpointAccess

# Verify attachment
aws iam list-attached-role-policies \
  --role-name JobTrackerLambdaRole \
  --query 'AttachedPolicies[?contains(PolicyName, `Pinpoint`)]'
```

---

## Step 6: Test WhatsApp Notifications

### 6.1 Test via AWS CLI

```bash
# Send test WhatsApp message via Pinpoint
aws pinpoint send-messages \
  --application-id YOUR_APP_ID \
  --message-request '{
    "Addresses": {
      "+60987654321": {
        "ChannelType": "SMS"
      }
    },
    "MessageConfiguration": {
      "SMSMessage": {
        "Body": "🔔 Test WhatsApp notification from Job Tracker!",
        "MessageType": "TRANSACTIONAL",
        "OriginationNumber": "+60123456789"
      }
    }
  }' \
  --region ap-southeast-5
```

**Expected Response:**
```json
{
  "MessageResponse": {
    "ApplicationId": "abc123def456",
    "Result": {
      "+60987654321": {
        "DeliveryStatus": "SUCCESSFUL",
        "MessageId": "msg-abc123",
        "StatusCode": 200,
        "StatusMessage": "Message has been accepted by phone carrier"
      }
    }
  }
}
```

### 6.2 Test via Job Submission

Submit a test job application:

```bash
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
      "requirements": "5+ years Python, AWS knowledge",
      "skills": ["Python", "AWS", "Lambda"],
      "description": "Exciting serverless role"
    }
  }'
```

Check:
1. **Response includes** `"whatsapp_notification": "sent"`
2. **WhatsApp received** on your phone
3. **CloudWatch logs** show "WhatsApp notification sent via Pinpoint"

### 6.3 Check Delivery Status

```bash
# View CloudWatch logs
aws logs tail /aws/lambda/job-tracker-api --follow --region ap-southeast-5

# Look for:
# "WhatsApp notification sent via Pinpoint: msg-abc123"
# "Pinpoint message sent successfully: msg-abc123"

# Get Pinpoint analytics (may take a few minutes)
aws pinpoint get-application-date-range-kpi \
  --application-id YOUR_APP_ID \
  --kpi-name messages-sent \
  --start-time 2025-11-02T00:00:00Z \
  --end-time 2025-11-03T00:00:00Z \
  --region ap-southeast-5
```

---

## Step 7: Monitor and Analytics

### 7.1 CloudWatch Metrics

Pinpoint automatically publishes metrics to CloudWatch:

```bash
# SMS delivery metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Pinpoint \
  --metric-name DeliveryRate \
  --dimensions Name=ApplicationId,Value=YOUR_APP_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region ap-southeast-5
```

### 7.2 Pinpoint Console Analytics

**Via Console:**
1. Pinpoint → **Analytics** → **Overview**
2. View:
   - Messages sent
   - Delivery rate
   - Failures
   - Engagement metrics

### 7.3 Set Up Alarms

```bash
# Create alarm for failed deliveries
aws cloudwatch put-metric-alarm \
  --alarm-name JobTrackerWhatsAppFailures \
  --alarm-description "Alert when WhatsApp messages fail" \
  --metric-name DeliveryFailures \
  --namespace AWS/Pinpoint \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ApplicationId,Value=YOUR_APP_ID \
  --region ap-southeast-5
```

---

## Troubleshooting

### Issue 1: "Application not found"

**Symptom:** `ResourceNotFoundException: Application with id 'xxx' not found`

**Solution:**
```bash
# Verify app exists
aws pinpoint get-apps --region ap-southeast-5

# Check region is correct
aws pinpoint get-app \
  --application-id YOUR_APP_ID \
  --region ap-southeast-5
```

### Issue 2: "Phone number not configured"

**Symptom:** `InvalidParameterException: OriginationNumber not found`

**Solution:**
```bash
# List available phone numbers
aws pinpoint-sms-voice-v2 describe-phone-numbers \
  --region ap-southeast-5

# Verify WhatsApp is enabled on the number
# Check: Capabilities includes "WHATSAPP"
```

### Issue 3: "Delivery failed"

**Symptom:** `DeliveryStatus: "PERMANENT_FAILURE"`

**Common causes:**
- Recipient number not in E.164 format
- WhatsApp not installed on recipient phone
- Recipient blocked your business number
- 24-hour window expired (use template instead)

**Solution:**
```bash
# Check CloudWatch logs for specific error
aws logs filter-log-events \
  --log-group-name /aws/lambda/job-tracker-api \
  --filter-pattern "Pinpoint" \
  --region ap-southeast-5 \
  --start-time $(date -u -d '30 minutes ago' +%s)000
```

### Issue 4: "Permission denied"

**Symptom:** `AccessDeniedException: User is not authorized`

**Solution:**
```bash
# Verify IAM policy attached
aws iam get-role-policy \
  --role-name JobTrackerLambdaRole \
  --policy-name JobTrackerPinpointAccess

# Re-attach if needed
aws iam attach-role-policy \
  --role-name JobTrackerLambdaRole \
  --policy-arn arn:aws:iam::460742884565:policy/JobTrackerPinpointAccess
```

### Issue 5: Messages sent but not received

**Check:**
1. Phone number format (E.164: `+60123456789`)
2. Recipient has WhatsApp installed
3. Business number not blocked by recipient
4. Sender name verified in WhatsApp Business profile
5. Message content complies with WhatsApp policies

---

## Production Checklist

Before going live:

- [ ] Pinpoint project created in correct region
- [ ] WhatsApp-enabled phone number provisioned
- [ ] Phone number verified and active
- [ ] Lambda environment variables configured
- [ ] IAM permissions attached to Lambda role
- [ ] Test message sent and received successfully
- [ ] CloudWatch logs show successful delivery
- [ ] Message templates created and approved (if needed)
- [ ] Analytics and monitoring configured
- [ ] Alerts set up for delivery failures
- [ ] Business verification completed (for production limits)

---

## Cost Estimates

**Amazon Pinpoint WhatsApp Pricing (as of 2025):**

- **User-initiated messages**: Free within 24-hour window
- **Business-initiated messages** (templates):
  - Malaysia: ~$0.01 USD per message
  - US: ~$0.02 USD per message
  - Varies by country

**Monthly costs (estimated):**
- 50 job applications/month
- All user-initiated (within 24-hour window)
- **Pinpoint**: $0 USD/month
- **Lambda**: Included in free tier
- **CloudWatch**: ~$0.50 USD/month (logs)
- **Total**: ~$0.50 USD/month

**Note:** Business verification may have one-time fees.

---

## Next Steps

After successful setup:

1. Deploy updated Lambda code with Pinpoint integration
2. Test automatic notifications on job submission
3. Test manual notifications from admin dashboard
4. Configure message templates for re-engagement
5. Set up two-way messaging (webhooks)
6. Monitor delivery metrics and optimize

---

## Additional Resources

- **Amazon Pinpoint Docs**: https://docs.aws.amazon.com/pinpoint/
- **SMS/WhatsApp Channel**: https://docs.aws.amazon.com/pinpoint/latest/userguide/channels-sms.html
- **Message Templates**: https://docs.aws.amazon.com/pinpoint/latest/userguide/message-templates.html
- **CloudWatch Metrics**: https://docs.aws.amazon.com/pinpoint/latest/userguide/monitoring-cloudwatch.html
- **WhatsApp Business Policies**: https://www.whatsapp.com/legal/business-policy/

---

**Setup Date:** 2025-11-02
**Status:** 📋 READY FOR IMPLEMENTATION
**Priority:** 🟢 FEATURE ENHANCEMENT

Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
