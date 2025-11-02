# WhatsApp Business API Setup Guide

## Step 1: Create WhatsApp Business Account

### 1.1 Prerequisites
- Facebook Business Account (create at https://business.facebook.com)
- Phone number for WhatsApp Business (cannot be currently registered on WhatsApp)
- Valid payment method (for Meta verification)

### 1.2 Create WhatsApp Business Account

1. Go to **Meta for Developers**: https://developers.facebook.com/
2. Click **My Apps** → **Create App**
3. Select **Business** as app type
4. Fill in app details:
   - App Name: `Job Tracker Notifications`
   - Contact Email: Your email
   - Business Account: Select or create new

### 1.3 Add WhatsApp Product

1. In your app dashboard, find **WhatsApp** in the products list
2. Click **Set Up**
3. Select or create a **WhatsApp Business Account**

### 1.4 Get Phone Number

**Option A: Use Test Number (for development)**
- Meta provides a test number automatically
- Good for initial testing
- Limited to 5 recipient numbers
- Messages expire after 24 hours

**Option B: Add Your Own Number (for production)**
1. Click **Add Phone Number**
2. Choose **Register New Number** or **Use Existing Number**
3. Enter your phone number (must not be registered on WhatsApp)
4. Verify via SMS code
5. Complete business verification (may take 1-3 days)

### 1.5 Get Credentials

After setup, you'll need these values:

1. **Phone Number ID**:
   - Go to **WhatsApp** → **API Setup**
   - Find `Phone number ID` (e.g., `123456789012345`)

2. **WhatsApp Business Account ID**:
   - Go to **WhatsApp** → **Getting Started**
   - Find `WhatsApp Business Account ID`

3. **Temporary Access Token** (for testing):
   - Go to **WhatsApp** → **API Setup**
   - Click **Generate Token**
   - **⚠️ Expires in 24 hours** - for testing only

4. **Permanent Access Token** (for production):
   ```bash
   # Generate system user access token
   # Go to Business Settings → System Users
   # Create new system user → Assign to WhatsApp app
   # Generate token with whatsapp_business_messaging permission
   ```

---

## Step 2: Configure Permanent Access Token

### 2.1 Create System User

1. Go to **Meta Business Suite**: https://business.facebook.com/settings
2. Navigate to **Users** → **System Users**
3. Click **Add** → Create system user:
   - Name: `JobTrackerBot`
   - Role: **Admin**
4. Click on the new system user
5. Click **Add Assets** → **Apps** → Select your app → **Full Control**
6. Click **Generate New Token**
   - Select your app
   - Select permissions:
     - ✅ `whatsapp_business_messaging`
     - ✅ `whatsapp_business_management`
   - Token expires: **Never** (or set custom duration)
7. **Copy the token** - you won't see it again!

### 2.2 Test Your Token

```bash
# Test API call
curl -X GET "https://graph.facebook.com/v20.0/me?access_token=YOUR_ACCESS_TOKEN"

# Should return: {"id":"YOUR_BUSINESS_ID"}
```

---

## Step 3: Configure Recipient Number

### 3.1 Add Test Recipient (Development)

While using test phone number, you can only send to pre-approved numbers:

1. Go to **WhatsApp** → **API Setup**
2. Under **To**, click **Manage Phone Number List**
3. Click **Add Phone Number**
4. Enter recipient number in E.164 format (e.g., `60123456789` for Malaysia)
5. Verify via WhatsApp code sent to that number

### 3.2 Production Recipients

Once your number is verified and app reviewed:
- No need to pre-approve recipients
- Can send to any valid WhatsApp number
- 24-hour conversation window applies

---

## Step 4: Store Credentials in AWS Secrets Manager

### 4.1 Create Secret

```bash
# Create WhatsApp credentials secret
aws secretsmanager create-secret \
  --name job-tracker-whatsapp \
  --description "WhatsApp Business API credentials for job tracker" \
  --secret-string '{
    "WHATSAPP_TOKEN": "EAAxxxxxxxxxxxxx",
    "PHONE_NUMBER_ID": "123456789012345",
    "BUSINESS_ACCOUNT_ID": "987654321098765",
    "RECIPIENT_NUMBER": "60123456789"
  }' \
  --region ap-southeast-5
```

### 4.2 Verify Secret

```bash
aws secretsmanager get-secret-value \
  --secret-id job-tracker-whatsapp \
  --region ap-southeast-5 \
  --query SecretString \
  --output text | jq '.'
```

### 4.3 Grant Lambda Permission

Update Lambda execution role to read secrets:

```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue"
  ],
  "Resource": "arn:aws:secretsmanager:ap-southeast-5:460742884565:secret:job-tracker-whatsapp-*"
}
```

---

## Step 5: Test Message Sending

### 5.1 Send Test Text Message

```bash
curl -X POST "https://graph.facebook.com/v20.0/PHONE_NUMBER_ID/messages" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "to": "60123456789",
    "type": "text",
    "text": {
      "preview_url": false,
      "body": "Hello from Job Tracker! This is a test message."
    }
  }'
```

### 5.2 Send Document (CV Test)

```bash
curl -X POST "https://graph.facebook.com/v20.0/PHONE_NUMBER_ID/messages" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "to": "60123456789",
    "type": "document",
    "document": {
      "link": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
      "filename": "test-cv.pdf"
    }
  }'
```

**Expected Response:**
```json
{
  "messaging_product": "whatsapp",
  "contacts": [
    {
      "input": "60123456789",
      "wa_id": "60123456789"
    }
  ],
  "messages": [
    {
      "id": "wamid.xxxxxxxxxxxxx"
    }
  ]
}
```

---

## Step 6: WhatsApp Message Templates (Optional)

For messages outside 24-hour conversation window, you need approved templates:

### 6.1 Create Template

1. Go to **WhatsApp Manager** → **Message Templates**
2. Click **Create Template**
3. Template example:
   ```
   Name: job_application_received
   Category: UTILITY
   Language: English

   Body:
   New job application received!

   Name: {{1}}
   Email: {{2}}
   Role: {{3}}

   CV attached. Please review.
   ```

4. Submit for approval (usually takes 1-2 hours)

### 6.2 Send Template Message

```bash
curl -X POST "https://graph.facebook.com/v20.0/PHONE_NUMBER_ID/messages" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "to": "60123456789",
    "type": "template",
    "template": {
      "name": "job_application_received",
      "language": { "code": "en" },
      "components": [
        {
          "type": "body",
          "parameters": [
            { "type": "text", "text": "John Doe" },
            { "type": "text", "text": "john@example.com" },
            { "type": "text", "text": "Senior Developer" }
          ]
        }
      ]
    }
  }'
```

---

## Common Issues & Solutions

### Issue 1: "Access token has expired"
**Solution:** Regenerate permanent token from System User (Step 2.1)

### Issue 2: "Recipient phone number not registered"
**Solution:**
- For test numbers: Add recipient to allowed list (Step 3.1)
- For production: Ensure number has WhatsApp installed

### Issue 3: "Document link not accessible"
**Solution:**
- Pre-signed S3 URLs must be publicly accessible
- Ensure URL doesn't require authentication
- URL must use HTTPS

### Issue 4: "Business verification required"
**Solution:**
- Complete Meta Business Verification
- Provide business documents
- May take 1-3 business days

### Issue 5: "Rate limit exceeded"
**Solution:**
- Test number: 10 messages per minute
- Production tier 1: 1,000 conversations per day
- Request higher tier if needed

---

## Production Checklist

Before going live:

- [ ] Business verification completed
- [ ] Production phone number added and verified
- [ ] Permanent access token generated and stored in Secrets Manager
- [ ] Recipient number(s) configured
- [ ] Test messages sent successfully
- [ ] Message templates created and approved (if needed)
- [ ] Lambda execution role has Secrets Manager permissions
- [ ] Error handling and logging configured
- [ ] Rate limiting considered
- [ ] Monitoring and alerts set up

---

## Useful Links

- **WhatsApp Cloud API Docs**: https://developers.facebook.com/docs/whatsapp/cloud-api
- **Getting Started**: https://developers.facebook.com/docs/whatsapp/cloud-api/get-started
- **Message Types**: https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-messages
- **Webhooks**: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks
- **Business Verification**: https://www.facebook.com/business/help/2058515294227817

---

## Next Steps

After completing this setup:

1. Update `WHATSAPP-SETUP.md` with your actual credentials (locally, don't commit!)
2. Store credentials in AWS Secrets Manager (Step 4)
3. Deploy updated Lambda code with WhatsApp integration
4. Test with real job application submission
5. Monitor CloudWatch logs for any issues

**Your credentials checklist:**
```bash
# Fill these in after setup:
WHATSAPP_TOKEN=EAAxxxxxxxxxxxxx
PHONE_NUMBER_ID=123456789012345
BUSINESS_ACCOUNT_ID=987654321098765
RECIPIENT_NUMBER=60123456789  # Your WhatsApp number in E.164 format
```

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
