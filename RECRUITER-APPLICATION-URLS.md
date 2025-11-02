# Recruiter Job Application URLs & API Reference

Complete guide for recruiter job application submission endpoints and usage.

---

## 🌐 Public Application URLs

### **Web Application Form (Recommended)**
```
https://cv.vgnshlv.nz/apply.html
```

**Features:**
- ✅ User-friendly web interface
- ✅ Hosted on CloudFront (fast, globally distributed)
- ✅ No authentication required (public endpoint)
- ✅ Automatic email notifications on submission
- ✅ Mobile responsive design
- ✅ Real-time form validation
- ✅ Secure file upload for job descriptions (PDF/DOCX)

**How to Use:**
1. Open the URL in a web browser
2. Fill out the recruiter information section
3. Complete the job details form
4. Optionally upload job description file
5. Click Submit
6. Receive confirmation with submission ID

---

## 🔌 API Endpoint (Direct Access)

### **Production API**

**Endpoint Pattern:**
```
POST https://{api-id}.execute-api.ap-southeast-5.amazonaws.com/prod/recruiter-submissions
```

**Stack Configuration:**
- Stack Name: `vgnshlvnz-job-tracker-stack`
- Region: `ap-southeast-5`
- Environment: `prod`

### **Getting Your Exact API URL**

**Method 1: CloudFormation Stack Output**
```bash
aws cloudformation describe-stacks \
  --stack-name vgnshlvnz-job-tracker-stack \
  --region ap-southeast-5 \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text
```

**Method 2: API Gateway List**
```bash
aws apigatewayv2 get-apis \
  --region ap-southeast-5 \
  --query 'Items[?Name==`JobTrackerApi`].[ApiEndpoint]' \
  --output text
```

**Method 3: AWS Console**
1. Go to AWS Console → CloudFormation
2. Select stack: `vgnshlvnz-job-tracker-stack`
3. Click "Outputs" tab
4. Look for `ApiEndpoint` value

---

## 📝 API Request Format

### **HTTP Method & Headers**
```
POST /recruiter-submissions
Content-Type: application/json
```

### **Request Body Schema**

```json
{
  "recruiter": {
    "name": "string (required, max 100 chars)",
    "email": "string (required, valid email)",
    "phone": "string (required, max 20 chars)",
    "agency": "string (optional, max 200 chars)"
  },
  "job": {
    "title": "string (required, max 200 chars)",
    "company": "string (required, max 200 chars)",
    "salary_min": "number (optional, non-negative)",
    "salary_max": "number (optional, non-negative)",
    "currency": "string (optional, default: MYR)",
    "requirements": "string (required, max 2000 chars)",
    "description": "string (optional, max 5000 chars)",
    "skills": "array of strings (optional, max 50 items, each max 100 chars)"
  }
}
```

### **Valid Currency Codes**
- `MYR` - Malaysian Ringgit
- `USD` - US Dollar
- `SGD` - Singapore Dollar
- `EUR` - Euro
- `GBP` - British Pound
- `AUD` - Australian Dollar
- `NZD` - New Zealand Dollar

### **Example Request**

```json
{
  "recruiter": {
    "name": "John Doe",
    "email": "john.doe@recruitingfirm.com",
    "phone": "+60123456789",
    "agency": "Tech Recruiters Inc"
  },
  "job": {
    "title": "Senior DevOps Engineer",
    "company": "Tech Corporation",
    "salary_min": 8000,
    "salary_max": 12000,
    "currency": "MYR",
    "requirements": "5+ years experience with AWS, Kubernetes, Docker, and CI/CD pipelines. Strong understanding of infrastructure as code.",
    "description": "We are looking for an experienced DevOps engineer to join our growing team. You will be responsible for maintaining our cloud infrastructure and implementing best practices.",
    "skills": [
      "AWS",
      "Kubernetes",
      "Docker",
      "Terraform",
      "Jenkins",
      "Python",
      "Linux"
    ]
  }
}
```

### **Success Response (200 OK)**

```json
{
  "submission_id": "rec_2025-11-02_abc12345",
  "jd_upload_url": "https://vgnshlvnz-job-tracker.s3.ap-southeast-5.amazonaws.com/...",
  "jd_upload_url_expires_in": 600,
  "created_at": "2025-11-02T11:30:00.000Z",
  "email_notification": "sent"
}
```

**Response Fields:**
- `submission_id`: Unique identifier for this submission
- `jd_upload_url`: Presigned S3 URL for uploading job description PDF (valid for 10 minutes)
- `jd_upload_url_expires_in`: URL expiry time in seconds (600 = 10 minutes)
- `created_at`: Submission timestamp (ISO 8601 format)
- `email_notification`: Status of email notification (`sent`, `failed`, `disabled`)

### **Error Responses**

**400 Bad Request - Validation Error**
```json
{
  "error": "ValidationError",
  "message": "Invalid email format"
}
```

**429 Too Many Requests - Rate Limit Exceeded**
```json
{
  "error": "RateLimitExceeded",
  "message": "Rate limit exceeded. Try again in 300 seconds"
}
```

**500 Internal Server Error**
```json
{
  "error": "InternalError",
  "message": "An unexpected error occurred"
}
```

---

## 🧪 Testing the API

### **Option 1: cURL (Command Line)**

```bash
# Replace {API_URL} with your actual API Gateway URL
curl -X POST "https://{API_URL}/prod/recruiter-submissions" \
  -H "Content-Type: application/json" \
  -d '{
    "recruiter": {
      "name": "Test Recruiter",
      "email": "test@example.com",
      "phone": "+60123456789",
      "agency": "Test Agency"
    },
    "job": {
      "title": "Software Engineer",
      "company": "Test Company",
      "salary_min": 5000,
      "salary_max": 8000,
      "currency": "MYR",
      "requirements": "Strong programming skills in Python and JavaScript",
      "skills": ["Python", "JavaScript", "React", "Node.js"]
    }
  }'
```

### **Option 2: Postman**

1. Create new POST request
2. URL: `https://{API_URL}/prod/recruiter-submissions`
3. Headers:
   - `Content-Type: application/json`
4. Body: Select "raw" → "JSON"
5. Paste example JSON request
6. Click Send

### **Option 3: Python**

```python
import requests
import json

url = "https://{API_URL}/prod/recruiter-submissions"
headers = {"Content-Type": "application/json"}
data = {
    "recruiter": {
        "name": "Test Recruiter",
        "email": "test@example.com",
        "phone": "+60123456789",
        "agency": "Test Agency"
    },
    "job": {
        "title": "Software Engineer",
        "company": "Test Company",
        "salary_min": 5000,
        "salary_max": 8000,
        "currency": "MYR",
        "requirements": "Strong programming skills",
        "skills": ["Python", "JavaScript"]
    }
}

response = requests.post(url, headers=headers, json=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

### **Option 4: JavaScript/Fetch**

```javascript
const url = "https://{API_URL}/prod/recruiter-submissions";
const data = {
  recruiter: {
    name: "Test Recruiter",
    email: "test@example.com",
    phone: "+60123456789",
    agency: "Test Agency"
  },
  job: {
    title: "Software Engineer",
    company: "Test Company",
    salary_min: 5000,
    salary_max: 8000,
    currency: "MYR",
    requirements: "Strong programming skills",
    skills: ["Python", "JavaScript"]
  }
};

fetch(url, {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify(data)
})
  .then(response => response.json())
  .then(data => console.log("Success:", data))
  .catch(error => console.error("Error:", error));
```

---

## 📧 Email Notifications

### **Automatic Notifications**

When a submission is created, an email notification is **automatically sent** to:
```
vigneshwaranravichandran11@outlook.com
```

**Email Contents:**
- 👤 Recruiter Information (name, email, phone, agency)
- 💼 Job Details (position, company, salary, skills)
- 📋 Requirements (full text)
- 📝 Description (if provided)
- 🔗 Direct link to dashboard with submission highlighted

### **Email Status Values**

- `sent` - Email successfully sent via Amazon SES
- `failed` - Email sending failed (check logs)
- `disabled` - Email notifications not configured
- `error` - Unexpected error during email sending

### **Manual Email Trigger (Admin Only)**

Admins can manually trigger email notifications from the dashboard:
```
POST /recruiter-submissions/{id}/send-email
Authorization: Bearer {cognito-jwt-token}
```

---

## 🔐 Security Features

### **Rate Limiting**
- **Limit**: 5 requests per 5 minutes per IP address
- **Purpose**: Prevent spam and abuse
- **Response**: HTTP 429 with retry-after information

### **Input Validation**
- ✅ All fields sanitized for XSS prevention
- ✅ Email format validation
- ✅ Phone number format validation
- ✅ String length limits enforced
- ✅ Null byte and control character filtering

### **File Upload Security**
- ✅ Magic byte validation (PDF/DOCX only)
- ✅ File size limits (5MB for JD, 10MB for CV)
- ✅ Presigned URLs with 10-minute expiry
- ✅ Virus scanning (if configured)

### **Security Headers**
All API responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`
- `Content-Security-Policy: default-src 'self'`
- `Referrer-Policy: strict-origin-when-cross-origin`

### **CORS Policy**
Allowed origins:
- `https://cv.vgnshlv.nz`
- `https://d1cda43lowke66.cloudfront.net`

---

## 🎯 Related Endpoints

### **Admin Dashboard**
```
https://cv.vgnshlv.nz/recruiter-dashboard.html
```
View, manage, and respond to recruiter submissions (requires authentication).

### **Admin API Endpoints (Authentication Required)**

**List All Submissions**
```
GET /recruiter-submissions
Authorization: Bearer {cognito-jwt-token}
```

**Get Single Submission**
```
GET /recruiter-submissions/{id}
Authorization: Bearer {cognito-jwt-token}
```

**Update Submission Status**
```
PUT /recruiter-submissions/{id}/status
Authorization: Bearer {cognito-jwt-token}
Content-Type: application/json

{
  "status": "contacted",
  "note": "Called recruiter, discussed requirements"
}
```

**Valid Status Values:**
- `new` - Initial submission
- `contacted` - Recruiter has been contacted
- `cv_sent` - CV sent to recruiter
- `closed` - Opportunity closed

---

## 📊 Monitoring & Debugging

### **CloudWatch Logs**
```bash
# View Lambda logs
aws logs tail /aws/lambda/JobTrackerLambda --follow --region ap-southeast-5

# Filter for recruiter submissions
aws logs tail /aws/lambda/JobTrackerLambda --follow --region ap-southeast-5 \
  --filter-pattern "recruiter-submissions"

# Check email notifications
aws logs tail /aws/lambda/JobTrackerLambda --follow --region ap-southeast-5 \
  --filter-pattern "Email sent"
```

### **Success Indicators in Logs**
```
Created recruiter submission: rec_2025-11-02_abc123
Email notification sent via SES: <message-id>
Email sent for submission: rec_2025-11-02_abc123, MessageId: <id>
```

### **Error Indicators in Logs**
```
ValidationError: Invalid email format
RateLimitExceeded: Rate limit exceeded
StorageError: Storage operation failed
```

### **SES Sending Statistics**
```bash
# Check SES quota
aws ses get-send-quota --region ap-southeast-1

# View sending statistics
aws ses get-send-statistics --region ap-southeast-1
```

---

## 🚀 Deployment Information

**Stack Details:**
- **Stack Name**: `vgnshlvnz-job-tracker-stack`
- **Region**: `ap-southeast-5` (Jakarta)
- **SES Region**: `ap-southeast-1` (Singapore)
- **Environment**: `prod`

**CloudFormation Template:**
- File: `template-job-tracker.yaml`
- Managed By: AWS SAM

**Deploy/Update Command:**
```bash
sam build --config-env job-tracker
sam deploy --config-env job-tracker
```

**View Stack Outputs:**
```bash
aws cloudformation describe-stacks \
  --stack-name vgnshlvnz-job-tracker-stack \
  --region ap-southeast-5 \
  --query 'Stacks[0].Outputs' \
  --output table
```

---

## 💰 Cost Breakdown

**API Gateway:**
- First 1M requests/month: **FREE** (Free Tier)
- Additional requests: $1.00 per million

**Lambda:**
- First 1M requests/month: **FREE** (Free Tier)
- Compute time: ~$0.20 per million requests

**S3 Storage:**
- First 5GB: **FREE** (Free Tier)
- Additional: $0.023/GB/month

**SES Email:**
- First 3,000 emails/month: **FREE** (via EC2/Lambda)
- Additional: $0.10 per 1,000 emails

**Estimated Monthly Cost** (50 submissions/month):
- API + Lambda: **$0.00** (within Free Tier)
- S3: **$0.01**
- SES: **$0.00** (within Free Tier)
- **Total: ~$0.01/month**

---

## 📚 Additional Resources

**Related Documentation:**
- `EMAIL-DEPLOYMENT-SUMMARY.md` - Email notification setup
- `AUTOMATED-EMAIL-FLOW.md` - Email flow documentation
- `SECURITY.md` - Security guidelines and best practices
- `template-job-tracker.yaml` - CloudFormation template

**AWS Services Used:**
- **API Gateway** (HTTP API)
- **Lambda** (Python 3.12 on ARM64/Graviton2)
- **S3** (Object storage with encryption)
- **SES** (Email notifications)
- **Cognito** (Authentication for admin endpoints)
- **CloudWatch** (Logging and monitoring)

**Support:**
- GitHub: https://github.com/vgnshlvnz/vgnshlvnz-s3-cv
- Issues: Create a GitHub issue for bugs or feature requests

---

## ✅ Quick Reference

| Resource | URL/Command |
|----------|-------------|
| **Application Form** | `https://cv.vgnshlv.nz/apply.html` |
| **API Endpoint** | `POST /recruiter-submissions` |
| **Dashboard** | `https://cv.vgnshlv.nz/recruiter-dashboard.html` |
| **Email Recipient** | `vigneshwaranravichandran11@outlook.com` |
| **Get API URL** | `aws cloudformation describe-stacks --stack-name vgnshlvnz-job-tracker-stack --region ap-southeast-5` |
| **View Logs** | `aws logs tail /aws/lambda/JobTrackerLambda --follow --region ap-southeast-5` |

---

**Last Updated**: 2025-11-02
**Status**: ✅ Production Ready
**Security**: ✅ All vulnerabilities fixed (17/17)

Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
