# Job Tracker API Documentation

## Overview

The Job Tracker API is a serverless REST API built on AWS Lambda and API Gateway that manages job application tracking with S3 storage and presigned URL-based CV uploads.

**Base URL**: `https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod`

**Region**: ap-southeast-5 (Asia Pacific - Malaysia)

**Authentication**: None (public API for job submissions)

---

## Table of Contents

1. [Endpoints](#endpoints)
2. [Data Schema](#data-schema)
3. [Error Handling](#error-handling)
4. [Rate Limiting](#rate-limiting)
5. [Examples](#examples)
6. [Testing](#testing)

---

## Endpoints

### 1. Create Application

Create a new job application and get a presigned URL for CV upload.

**Endpoint**: `POST /applications`

**Request Body**:
```json
{
  "job_title": "Senior DevOps Engineer",
  "company_name": "TechCorp Malaysia",
  "agency_name": "TechStaff Recruitment",
  "caller": {
    "name": "Sarah Chen",
    "email": "sarah@techstaff.com.my",
    "phone": "+60-12-3456789"
  },
  "caller_method": "email",
  "salary": {
    "currency": "MYR",
    "min": 8000,
    "max": 15000,
    "period": "monthly"
  },
  "perks": ["medical", "bonus", "remote-2d"],
  "details": {
    "roles": "Build and maintain cloud infrastructure",
    "responsibilities": [
      "Design REST APIs",
      "Own CI/CD pipeline",
      "On-call rotation"
    ],
    "skillsets": ["Python", "AWS", "Docker", "Kubernetes"],
    "questions_asked": ["notice period", "visa support"],
    "info_provided": ["portfolio link", "availability"]
  },
  "tags": ["priority", "backend", "aws"]
}
```

**Response** (200 OK):
```json
{
  "application_id": "app_2025-11-01_a1b2c3d4",
  "cv_upload_url": "https://vgnshlvnz-job-tracker.s3.ap-southeast-5.amazonaws.com/applications/2025/app_2025-11-01_a1b2c3d4/cv.pdf?X-Amz-Algorithm=...",
  "cv_upload_url_expires_in": 900,
  "created_at": "2025-11-01T10:22:15Z"
}
```

**curl Example**:
```bash
curl -X POST https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications \
  -H "Content-Type: application/json" \
  -d '{
    "job_title": "Senior DevOps Engineer",
    "company_name": "TechCorp",
    "caller": {
      "name": "Sarah Chen",
      "email": "sarah@techstaff.com.my",
      "phone": "+60-12-3456789"
    },
    "caller_method": "email",
    "salary": {
      "currency": "MYR",
      "min": 8000,
      "max": 15000,
      "period": "monthly"
    }
  }'
```

---

### 2. Upload CV

After creating an application, use the presigned URL to upload the CV file.

**Method**: `PUT` to the presigned URL

**Headers**:
- `Content-Type: application/pdf`

**Body**: Binary PDF file

**curl Example**:
```bash
# Get the presigned URL from the create response
CV_UPLOAD_URL="<url_from_create_response>"

# Upload CV
curl -X PUT "$CV_UPLOAD_URL" \
  -H "Content-Type: application/pdf" \
  --data-binary @"/path/to/cv.pdf"
```

**JavaScript Example**:
```javascript
const cvFile = document.getElementById('cvInput').files[0];

await fetch(cvUploadUrl, {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/pdf'
  },
  body: cvFile
});
```

---

### 3. List Applications

Retrieve a list of all job applications with optional filtering.

**Endpoint**: `GET /applications`

**Query Parameters**:
- `status` (optional): Filter by status (`applied`, `screening`, `interview`, `offer`, `rejected`, `withdrawn`)
- `limit` (optional): Maximum number of results (default: 100, max: 1000)

**Response** (200 OK):
```json
{
  "applications": [
    {
      "application_id": "app_2025-11-01_a1b2c3d4",
      "created_at": "2025-11-01T10:22:15Z",
      "updated_at": "2025-11-01T10:22:15Z",
      "status": "applied",
      "job_title": "Senior DevOps Engineer",
      "company_name": "TechCorp Malaysia",
      "agency_name": "TechStaff Recruitment",
      "salary_max": 15000,
      "tags": ["priority", "backend", "aws"]
    },
    {
      "application_id": "app_2025-10-28_x9y8z7w6",
      "created_at": "2025-10-28T14:10:00Z",
      "updated_at": "2025-10-28T14:10:00Z",
      "status": "screening",
      "job_title": "Cloud Engineer",
      "company_name": "CloudTech Sdn Bhd",
      "agency_name": null,
      "salary_max": 12000,
      "tags": ["cloud", "aws"]
    }
  ],
  "count": 2,
  "filters": {
    "status": null,
    "limit": 100
  }
}
```

**curl Examples**:
```bash
# List all applications
curl https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications

# Filter by status
curl "https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications?status=applied"

# Limit results
curl "https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications?limit=10"

# Combine filters
curl "https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications?status=interview&limit=5"
```

---

### 4. Get Application

Retrieve details of a specific application including CV download URL.

**Endpoint**: `GET /applications/{id}`

**Path Parameters**:
- `id`: Application ID (e.g., `app_2025-11-01_a1b2c3d4`)

**Response** (200 OK):
```json
{
  "application_id": "app_2025-11-01_a1b2c3d4",
  "created_at": "2025-11-01T10:22:15Z",
  "updated_at": "2025-11-01T10:22:15Z",
  "status": "applied",
  "job_title": "Senior DevOps Engineer",
  "company_name": "TechCorp Malaysia",
  "agency_name": "TechStaff Recruitment",
  "caller": {
    "name": "Sarah Chen",
    "email": "sarah@techstaff.com.my",
    "phone": "+60-12-3456789"
  },
  "caller_method": "email",
  "salary": {
    "currency": "MYR",
    "min": 8000,
    "max": 15000,
    "period": "monthly"
  },
  "perks": ["medical", "bonus", "remote-2d"],
  "details": {
    "roles": "Build and maintain cloud infrastructure",
    "responsibilities": ["Design REST APIs", "Own CI/CD pipeline"],
    "skillsets": ["Python", "AWS", "Docker"],
    "questions_asked": ["notice period"],
    "info_provided": ["portfolio link"]
  },
  "cv_key": "applications/2025/app_2025-11-01_a1b2c3d4/cv.pdf",
  "cv_download_url": "https://vgnshlvnz-job-tracker.s3.ap-southeast-5.amazonaws.com/applications/2025/app_2025-11-01_a1b2c3d4/cv.pdf?X-Amz-Algorithm=...",
  "cv_download_url_expires_in": 900,
  "tags": ["priority", "backend", "aws"]
}
```

**curl Example**:
```bash
curl https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications/app_2025-11-01_a1b2c3d4
```

---

### 5. Update Application

Update an existing job application.

**Endpoint**: `PUT /applications/{id}`

**Path Parameters**:
- `id`: Application ID

**Request Body** (partial update - only include fields to update):
```json
{
  "status": "interview",
  "tags": ["priority", "backend", "aws", "shortlisted"]
}
```

**Response** (200 OK):
```json
{
  "application_id": "app_2025-11-01_a1b2c3d4",
  "updated": true,
  "updated_at": "2025-11-01T15:30:00Z"
}
```

**Updatable Fields**:
- `status`
- `job_title`
- `agency_name`
- `company_name`
- `caller`
- `caller_method`
- `salary`
- `perks`
- `details`
- `tags`

**Protected Fields** (cannot be updated):
- `application_id`
- `created_at`
- `cv_key`

**curl Example**:
```bash
curl -X PUT https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications/app_2025-11-01_a1b2c3d4 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "interview",
    "details": {
      "info_provided": ["Scheduled interview for Nov 5"]
    }
  }'
```

---

### 6. Delete Application

Delete a job application and all associated files (metadata + CV).

**Endpoint**: `DELETE /applications/{id}`

**Path Parameters**:
- `id`: Application ID

**Response** (200 OK):
```json
{
  "application_id": "app_2025-11-01_a1b2c3d4",
  "deleted": true,
  "files_deleted": 2
}
```

**curl Example**:
```bash
curl -X DELETE https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications/app_2025-11-01_a1b2c3d4
```

---

### 7. Get CV Upload URL

Get a fresh presigned URL for CV upload (e.g., if original URL expired).

**Endpoint**: `POST /applications/{id}/cv-upload-url`

**Path Parameters**:
- `id`: Application ID

**Response** (200 OK):
```json
{
  "application_id": "app_2025-11-01_a1b2c3d4",
  "cv_upload_url": "https://vgnshlvnz-job-tracker.s3.ap-southeast-5.amazonaws.com/...",
  "cv_upload_url_expires_in": 900,
  "content_type": "application/pdf",
  "max_size_bytes": 10485760
}
```

**curl Example**:
```bash
curl -X POST https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications/app_2025-11-01_a1b2c3d4/cv-upload-url
```

---

## Data Schema

### Application Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `application_id` | string | Auto-generated | Unique ID: `app_YYYY-MM-DD_UUID` |
| `created_at` | string (ISO 8601) | Auto-generated | Creation timestamp (UTC) |
| `updated_at` | string (ISO 8601) | Auto-generated | Last update timestamp (UTC) |
| `status` | string | No (default: "applied") | Application status |
| `job_title` | string | Yes | Job position title |
| `company_name` | string | Yes | Hiring company name |
| `agency_name` | string | No | Recruitment agency name |
| `caller` | object | Yes | Recruiter contact info |
| `caller.name` | string | Yes | Recruiter name |
| `caller.email` | string | Yes | Recruiter email |
| `caller.phone` | string | No | Recruiter phone |
| `caller_method` | string | No | Contact method (email/phone/linkedin/portal) |
| `salary` | object | No | Salary information |
| `salary.currency` | string | No (default: "MYR") | Currency code |
| `salary.min` | number | No | Minimum salary |
| `salary.max` | number | No | Maximum salary |
| `salary.period` | string | No (default: "monthly") | Pay period |
| `perks` | array | No | Benefits list |
| `details` | object | No | Job details |
| `details.roles` | string | No | Role description |
| `details.responsibilities` | array | No | List of responsibilities |
| `details.skillsets` | array | No | Required skills |
| `details.questions_asked` | array | No | Questions from recruiter |
| `details.info_provided` | array | No | Info provided to recruiter |
| `cv_key` | string | Auto-generated | S3 key for CV file |
| `tags` | array | No | Custom tags for filtering |

### Status Values

- `applied` - Application submitted
- `screening` - Under review
- `interview` - Interview scheduled/completed
- `offer` - Offer received
- `rejected` - Application rejected
- `withdrawn` - Candidate withdrawn

---

## Error Handling

### Error Response Format

```json
{
  "error": "ErrorType",
  "message": "Human-readable error message"
}
```

### HTTP Status Codes

| Code | Error Type | Description |
|------|------------|-------------|
| 200 | Success | Request successful |
| 400 | InvalidRequest | Missing required fields or invalid data |
| 400 | InvalidJSON | Request body is not valid JSON |
| 404 | NotFound | Application ID not found |
| 500 | S3Error | S3 storage error |
| 500 | InternalError | Unexpected server error |

### Example Error Responses

**400 Bad Request**:
```json
{
  "error": "InvalidRequest",
  "message": "Missing application ID"
}
```

**404 Not Found**:
```json
{
  "error": "NotFound",
  "message": "Application not found: app_2025-11-01_invalid"
}
```

**500 Internal Server Error**:
```json
{
  "error": "InternalError",
  "message": "Internal server error: <details>"
}
```

---

## Rate Limiting

**Current Limits**:
- Burst: 100 requests
- Rate: 50 requests/second

**Response Headers**:
- `X-RateLimit-Limit`: Maximum requests per second
- `X-RateLimit-Remaining`: Remaining requests in current window

**429 Too Many Requests**:
```json
{
  "error": "ThrottlingException",
  "message": "Rate exceeded"
}
```

---

## Examples

### Complete Application Workflow

```bash
#!/bin/bash
API_BASE="https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod"

# 1. Create application
RESPONSE=$(curl -s -X POST "$API_BASE/applications" \
  -H "Content-Type: application/json" \
  -d '{
    "job_title": "DevOps Engineer",
    "company_name": "TechCorp",
    "caller": {
      "name": "Sarah Chen",
      "email": "sarah@techstaff.com.my",
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
      "skillsets": ["Python", "AWS", "Docker"]
    }
  }')

echo "Create response: $RESPONSE"

# 2. Extract application ID and upload URL
APP_ID=$(echo "$RESPONSE" | jq -r '.application_id')
UPLOAD_URL=$(echo "$RESPONSE" | jq -r '.cv_upload_url')

echo "Application ID: $APP_ID"

# 3. Upload CV
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: application/pdf" \
  --data-binary @"cv.pdf"

echo "CV uploaded successfully"

# 4. Get application details
curl -s "$API_BASE/applications/$APP_ID" | jq '.'

# 5. Update status
curl -s -X PUT "$API_BASE/applications/$APP_ID" \
  -H "Content-Type: application/json" \
  -d '{"status": "screening"}' | jq '.'

# 6. List all applications
curl -s "$API_BASE/applications" | jq '.applications[] | {id: .application_id, title: .job_title, status: .status}'
```

---

## Testing

### Health Check

```bash
# Test if API is responding
curl -I https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications

# Expected: HTTP/2 200
```

### Test Suite

```bash
# 1. Create test application
APP_ID=$(curl -s -X POST "$API_BASE/applications" \
  -H "Content-Type: application/json" \
  -d '{"job_title":"Test","company_name":"Test Corp","caller":{"name":"Test","email":"test@example.com"}}' \
  | jq -r '.application_id')

echo "Created: $APP_ID"

# 2. Verify it exists
curl -s "$API_BASE/applications/$APP_ID" | jq '.job_title'

# 3. Update it
curl -s -X PUT "$API_BASE/applications/$APP_ID" \
  -H "Content-Type: application/json" \
  -d '{"status":"rejected"}' | jq '.'

# 4. Delete it
curl -s -X DELETE "$API_BASE/applications/$APP_ID" | jq '.'

# 5. Verify deletion (should return 404)
curl -s "$API_BASE/applications/$APP_ID" | jq '.'
```

---

## CORS Configuration

**Allowed Origins**:
- `https://cv.vgnshlv.nz`
- `https://d1cda43lowke66.cloudfront.net`
- `http://localhost:*` (for local development)

**Allowed Methods**:
- GET
- POST
- PUT
- DELETE
- OPTIONS

**Allowed Headers**:
- `content-type`
- `authorization`
- `x-api-key`

---

## Presigned URL Notes

**Expiry Time**: 900 seconds (15 minutes)

**Security**:
- URLs are temporary and expire after 15 minutes
- Each URL is unique and can only be used once
- Content-Type is enforced (`application/pdf`)
- No authentication required for upload (secure by obscurity)

**Best Practices**:
1. Use the presigned URL immediately after receiving it
2. If expired, request a new URL via `POST /applications/{id}/cv-upload-url`
3. Always set `Content-Type: application/pdf` when uploading
4. File size limit: 10 MB

---

## Changelog

### Version 1.0 (November 1, 2025)
- Initial API release
- CRUD operations for job applications
- Presigned URL-based CV uploads
- S3-based storage
- Tag-based filtering

---

## Support

For issues or questions:
- Email: vigneshwaranravichandran11@outlook.com
- GitHub: https://github.com/vgnshlvnz/vgnshlvnz-s3-cv

---

**API Version**: 1.0
**Last Updated**: November 1, 2025
**Region**: ap-southeast-5 (Malaysia)
