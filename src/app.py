"""
Job Tracker Lambda Function
Handles CRUD operations for job applications stored in S3
"""

import json
import os
import uuid
import logging
import re
import time
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from html import escape
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
import jwt
from jwt import PyJWKClient
from collections import defaultdict

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Import WhatsApp notification module
try:
    from whatsapp_notifier import send_application_notification, is_whatsapp_enabled
    WHATSAPP_AVAILABLE = True
except ImportError as e:
    logger.warning(f"WhatsApp notifier not available: {e}")
    WHATSAPP_AVAILABLE = False

# Environment variables
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'vgnshlvnz-job-tracker')
PRESIGNED_URL_EXPIRY = int(os.environ.get('PRESIGNED_URL_EXPIRY', '900'))
REGION = os.environ.get('REGION', 'ap-southeast-5')

# Cognito configuration for JWT validation
USER_POOL_ID = os.environ.get('USER_POOL_ID', 'ap-southeast-5_0QQg8Wd6r')
CLIENT_ID = os.environ.get('CLIENT_ID', '4f8f3qon7v6tegud4qe854epo6')
COGNITO_ISSUER = f'https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}'

# Presigned URL expiry times (in seconds)
DOWNLOAD_URL_EXPIRY = 300  # 5 minutes
UPLOAD_URL_EXPIRY = 600    # 10 minutes

# Allowed origins for CORS
ALLOWED_ORIGINS = [
    'https://cv.vgnshlv.nz',
    'https://d1cda43lowke66.cloudfront.net'
]

# AWS clients
s3 = boto3.client(
    's3',
    region_name=REGION,
    config=Config(
        signature_version='s3v4',
        s3={'addressing_style': 'virtual'}
    )
)

# Constants
ALLOWED_CV_TYPES = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
ALLOWED_JD_TYPES = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
MAX_CV_SIZE = 10 * 1024 * 1024  # 10MB
MAX_JD_SIZE = 5 * 1024 * 1024   # 5MB


def _app_prefix(app_id: str) -> str:
    """
    Get S3 prefix for application folder
    app_2025-11-01_abc123 -> applications/2025/app_2025-11-01_abc123/
    """
    try:
        # Extract year from app_id: app_YYYY-MM-DD_uuid
        date_part = app_id.split('_')[1]  # "2025-11-01"
        year = date_part.split('-')[0]     # "2025"
        return f"applications/{year}/{app_id}/"
    except (IndexError, ValueError) as e:
        logger.error(f"Invalid app_id format: {app_id}")
        raise ValueError(f"Invalid application ID format: {app_id}")


def _generate_app_id() -> str:
    """Generate unique application ID: app_YYYY-MM-DD_UUID"""
    today = date.today().isoformat()  # "2025-11-01"
    unique_id = uuid.uuid4().hex[:8]  # 8 characters
    return f"app_{today}_{unique_id}"


def _utc_now() -> str:
    """Get current UTC timestamp in ISO format"""
    return datetime.utcnow().isoformat() + "Z"


def _rec_prefix(rec_id: str) -> str:
    """
    Get S3 prefix for recruiter submission folder
    rec_2025-11-01_abc123 -> recruiters/2025/rec_2025-11-01_abc123/
    """
    try:
        # Extract year from rec_id: rec_YYYY-MM-DD_uuid
        date_part = rec_id.split('_')[1]  # "2025-11-01"
        year = date_part.split('-')[0]     # "2025"
        return f"recruiters/{year}/{rec_id}/"
    except (IndexError, ValueError) as e:
        logger.error(f"Invalid rec_id format: {rec_id}")
        raise ValueError(f"Invalid submission ID format: {rec_id}")


def _generate_rec_id() -> str:
    """Generate unique recruiter submission ID: rec_YYYY-MM-DD_UUID"""
    today = date.today().isoformat()  # "2025-11-01"
    unique_id = uuid.uuid4().hex[:8]  # 8 characters
    return f"rec_{today}_{unique_id}"


# ========== SECURITY FUNCTIONS ==========

# In-memory rate limiter (use DynamoDB for production with multiple Lambda instances)
rate_limit_store = defaultdict(list)

def validate_token(event: Dict) -> Optional[Dict]:
    """
    Validate Cognito JWT token from Authorization header
    Returns decoded token payload if valid, raises exception otherwise
    """
    try:
        # Get Authorization header
        headers = event.get('headers', {})
        auth_header = headers.get('authorization') or headers.get('Authorization', '')

        if not auth_header:
            raise ValueError("Missing Authorization header")

        if not auth_header.startswith('Bearer '):
            raise ValueError("Invalid Authorization header format. Expected 'Bearer <token>'")

        token = auth_header.split(' ')[1]

        # Get Cognito public keys
        jwks_url = f"{COGNITO_ISSUER}/.well-known/jwks.json"
        jwks_client = PyJWKClient(jwks_url, cache_keys=True)

        # Get signing key from token
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and validate token
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=COGNITO_ISSUER,
            options={"verify_exp": True}
        )

        logger.info(f"Token validated for user: {decoded.get('email', decoded.get('sub'))}")
        return decoded

    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidAudienceError:
        raise ValueError("Invalid token audience")
    except jwt.InvalidIssuerError:
        raise ValueError("Invalid token issuer")
    except jwt.DecodeError:
        raise ValueError("Invalid token format")
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise ValueError(f"Token validation failed: {str(e)}")


def is_admin(user: Dict) -> bool:
    """Check if user has admin role"""
    # Check custom:role attribute from Cognito
    role = user.get('custom:role', '').lower()
    return role == 'admin'


def check_rate_limit(ip: str, limit: int = 5, window: int = 300) -> Tuple[bool, str]:
    """
    Check if IP exceeds rate limit
    limit: max requests per window
    window: time window in seconds (default: 5 minutes)
    """
    now = time.time()
    cutoff = now - window

    # Clean old requests
    rate_limit_store[ip] = [t for t in rate_limit_store[ip] if t > cutoff]

    # Check limit
    if len(rate_limit_store[ip]) >= limit:
        retry_after = int(cutoff + window - now)
        return False, f"Rate limit exceeded. Try again in {retry_after} seconds"

    # Add current request
    rate_limit_store[ip].append(now)
    return True, ""


def sanitize_event_for_logging(event: Dict) -> Dict:
    """Remove sensitive data from event before logging"""
    safe_event = event.copy()

    # Remove headers with sensitive data
    if 'headers' in safe_event:
        safe_headers = {}
        for key, value in safe_event['headers'].items():
            if key.lower() in ['authorization', 'cookie', 'x-api-key']:
                safe_headers[key] = '***REDACTED***'
            else:
                safe_headers[key] = value
        safe_event['headers'] = safe_headers

    # Redact PII from body
    if 'body' in safe_event and safe_event['body']:
        try:
            body = json.loads(safe_event['body'])
            if 'recruiter' in body:
                if 'email' in body['recruiter']:
                    body['recruiter']['email'] = '***@***.***'
                if 'phone' in body['recruiter']:
                    body['recruiter']['phone'] = '+**-**-***'
            safe_event['body'] = json.dumps(body)
        except:
            safe_event['body'] = '***REDACTED***'

    return safe_event


def sanitize_submission_for_recruiter(meta: Dict) -> Dict:
    """Remove sensitive admin fields for non-admin users"""
    safe_fields = {
        'submission_id', 'created_at', 'updated_at', 'status',
        'recruiter', 'job', 'files', 'type'
    }
    return {k: v for k, v in meta.items() if k in safe_fields}


# ========== INPUT VALIDATION FUNCTIONS ==========

def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email format"""
    if not email or len(email) > 254:
        return False, "Invalid email length"

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"

    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    """Validate phone number"""
    if not phone or len(phone) > 20:
        return False, "Invalid phone length"

    # Allow only digits, +, -, (, ), spaces
    pattern = r'^[\d\s\+\-\(\)]+$'
    if not re.match(pattern, phone):
        return False, "Invalid phone format"

    return True, ""


def validate_string(value: str, max_length: int, field_name: str, required: bool = True) -> Tuple[bool, str]:
    """Validate string field"""
    if not value:
        if required:
            return False, f"{field_name} is required"
        return True, ""

    if len(value) > max_length:
        return False, f"{field_name} exceeds {max_length} characters"

    # Check for null bytes and control characters
    if '\x00' in value or any(ord(c) < 32 and c not in '\t\n\r' for c in value):
        return False, f"{field_name} contains invalid characters"

    return True, ""


def validate_id_format(id_value: str, prefix: str) -> bool:
    """Validate ID format to prevent path traversal"""
    pattern = f'^{prefix}_\\d{{4}}-\\d{{2}}-\\d{{2}}_[a-f0-9]{{8}}$'
    return bool(re.match(pattern, id_value))


def validate_status(status: str) -> Tuple[bool, str]:
    """Validate status value"""
    valid_statuses = ['new', 'contacted', 'cv_sent', 'closed']
    if status not in valid_statuses:
        return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
    return True, ""


def sanitize_for_display(value: str) -> str:
    """Sanitize string for HTML display"""
    return escape(value)


def _response(status_code: int, body: Dict[str, Any], headers: Optional[Dict] = None, event: Optional[Dict] = None) -> Dict:
    """Build API Gateway response with secure CORS"""
    # Get origin from request
    origin = ''
    if event:
        request_headers = event.get('headers', {})
        origin = request_headers.get('origin') or request_headers.get('Origin', '')

    # Check if origin is allowed
    allowed_origin = ALLOWED_ORIGINS[0]  # Default to first allowed origin
    if origin in ALLOWED_ORIGINS:
        allowed_origin = origin

    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': allowed_origin,
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Access-Control-Allow-Credentials': 'false'
    }
    if headers:
        default_headers.update(headers)

    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body, ensure_ascii=False, indent=2)
    }


def _error_response(status_code: int, message: str, error_type: str = 'Error', event: Optional[Dict] = None) -> Dict:
    """Build error response"""
    logger.error(f"{error_type}: {message}")
    return _response(status_code, {
        'error': error_type,
        'message': message
    }, event=event)


def create_application(event: Dict) -> Dict:
    """
    POST /applications
    Create new job application
    """
    try:
        body = json.loads(event.get('body') or '{}')

        # Generate application ID
        app_id = _generate_app_id()
        prefix = _app_prefix(app_id)

        # Build metadata following the schema
        meta = {
            "application_id": app_id,
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "status": body.get("status", "applied"),
            "job_title": body.get("job_title", ""),
            "agency_name": body.get("agency_name", ""),
            "company_name": body.get("company_name", ""),
            "caller": {
                "name": body.get("caller", {}).get("name", ""),
                "email": body.get("caller", {}).get("email", ""),
                "phone": body.get("caller", {}).get("phone", "")
            },
            "caller_method": body.get("caller_method", ""),
            "salary": {
                "currency": body.get("salary", {}).get("currency", "MYR"),
                "min": body.get("salary", {}).get("min", 0),
                "max": body.get("salary", {}).get("max", 0),
                "period": body.get("salary", {}).get("period", "monthly")
            },
            "perks": body.get("perks", []),
            "details": {
                "roles": body.get("details", {}).get("roles", ""),
                "responsibilities": body.get("details", {}).get("responsibilities", []),
                "skillsets": body.get("details", {}).get("skillsets", []),
                "questions_asked": body.get("details", {}).get("questions_asked", []),
                "info_provided": body.get("details", {}).get("info_provided", [])
            },
            "cv_key": f"{prefix}cv.pdf",
            "tags": body.get("tags", [])
        }

        # Save metadata to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=f"{prefix}meta.json",
            Body=json.dumps(meta, ensure_ascii=False, indent=2).encode('utf-8'),
            ContentType="application/json",
            Metadata={
                'application-id': app_id,
                'created-at': meta['created_at']
            }
        )

        # Generate presigned URL for CV upload
        cv_upload_url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                "Bucket": BUCKET_NAME,
                "Key": meta["cv_key"],
                "ContentType": "application/pdf"
            },
            ExpiresIn=PRESIGNED_URL_EXPIRY
        )

        logger.info(f"Created application: {app_id}")

        return _response(200, {
            "application_id": app_id,
            "cv_upload_url": cv_upload_url,
            "cv_upload_url_expires_in": PRESIGNED_URL_EXPIRY,
            "created_at": meta["created_at"]
        })

    except json.JSONDecodeError as e:
        return _error_response(400, f"Invalid JSON: {str(e)}", "InvalidJSON")
    except ClientError as e:
        return _error_response(500, f"S3 error: {str(e)}", "S3Error")
    except Exception as e:
        logger.exception("Unexpected error in create_application")
        return _error_response(500, f"Internal error: {str(e)}", "InternalError")


def list_applications(event: Dict) -> Dict:
    """
    GET /applications
    List all job applications with optional filters
    """
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        status_filter = query_params.get('status')
        limit = min(int(query_params.get('limit', '100')), 1000)

        applications = []

        # List all year folders
        logger.info(f"Listing applications from bucket: {BUCKET_NAME}")

        # List applications prefix
        paginator = s3.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(
            Bucket=BUCKET_NAME,
            Prefix='applications/',
            Delimiter='/'
        )

        # Get all year folders
        years = []
        for page in page_iterator:
            for prefix in page.get('CommonPrefixes', []):
                year_prefix = prefix['Prefix']
                years.append(year_prefix)

        # For each year, list applications
        for year_prefix in years:
            app_paginator = s3.get_paginator('list_objects_v2')
            app_page_iterator = app_paginator.paginate(
                Bucket=BUCKET_NAME,
                Prefix=year_prefix,
                Delimiter='/'
            )

            for page in app_page_iterator:
                for app_prefix in page.get('CommonPrefixes', []):
                    app_folder = app_prefix['Prefix']
                    meta_key = f"{app_folder}meta.json"

                    try:
                        # Get meta.json for each application
                        obj = s3.get_object(Bucket=BUCKET_NAME, Key=meta_key)
                        meta = json.loads(obj['Body'].read().decode('utf-8'))

                        # Apply status filter if provided
                        if status_filter and meta.get('status') != status_filter:
                            continue

                        # Add summary info (not full meta)
                        applications.append({
                            "application_id": meta.get("application_id"),
                            "created_at": meta.get("created_at"),
                            "updated_at": meta.get("updated_at"),
                            "status": meta.get("status"),
                            "job_title": meta.get("job_title"),
                            "company_name": meta.get("company_name"),
                            "agency_name": meta.get("agency_name"),
                            "salary_max": meta.get("salary", {}).get("max"),
                            "tags": meta.get("tags", [])
                        })

                        # Limit results
                        if len(applications) >= limit:
                            break

                    except ClientError as e:
                        logger.warning(f"Could not read {meta_key}: {str(e)}")
                        continue

                if len(applications) >= limit:
                    break

            if len(applications) >= limit:
                break

        # Sort by created_at descending (newest first)
        applications.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        logger.info(f"Found {len(applications)} applications")

        return _response(200, {
            "applications": applications,
            "count": len(applications),
            "filters": {
                "status": status_filter,
                "limit": limit
            }
        })

    except ClientError as e:
        return _error_response(500, f"S3 error: {str(e)}", "S3Error")
    except Exception as e:
        logger.exception("Unexpected error in list_applications")
        return _error_response(500, f"Internal error: {str(e)}", "InternalError")


def get_application(event: Dict) -> Dict:
    """
    GET /applications/{id}
    Get single application with download URL
    """
    try:
        path_params = event.get('pathParameters') or {}
        app_id = path_params.get('id')

        if not app_id:
            return _error_response(400, "Missing application ID", "InvalidRequest")

        # Get metadata
        prefix = _app_prefix(app_id)
        meta_key = f"{prefix}meta.json"

        try:
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=meta_key)
            meta = json.loads(obj['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return _error_response(404, f"Application not found: {app_id}", "NotFound")
            raise

        # Generate presigned download URL for CV
        cv_key = meta.get("cv_key")
        cv_download_url = None

        if cv_key:
            try:
                # Check if CV exists
                s3.head_object(Bucket=BUCKET_NAME, Key=cv_key)
                cv_download_url = s3.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={
                        "Bucket": BUCKET_NAME,
                        "Key": cv_key
                    },
                    ExpiresIn=PRESIGNED_URL_EXPIRY
                )
            except ClientError:
                logger.warning(f"CV not found for {app_id}: {cv_key}")

        meta["cv_download_url"] = cv_download_url
        meta["cv_download_url_expires_in"] = PRESIGNED_URL_EXPIRY if cv_download_url else None

        logger.info(f"Retrieved application: {app_id}")

        return _response(200, meta)

    except ValueError as e:
        return _error_response(400, str(e), "InvalidRequest")
    except ClientError as e:
        return _error_response(500, f"S3 error: {str(e)}", "S3Error")
    except Exception as e:
        logger.exception("Unexpected error in get_application")
        return _error_response(500, f"Internal error: {str(e)}", "InternalError")


def update_application(event: Dict) -> Dict:
    """
    PUT /applications/{id}
    Update application metadata
    """
    try:
        path_params = event.get('pathParameters') or {}
        app_id = path_params.get('id')

        if not app_id:
            return _error_response(400, "Missing application ID", "InvalidRequest")

        body = json.loads(event.get('body') or '{}')

        # Get existing metadata
        prefix = _app_prefix(app_id)
        meta_key = f"{prefix}meta.json"

        try:
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=meta_key)
            meta = json.loads(obj['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return _error_response(404, f"Application not found: {app_id}", "NotFound")
            raise

        # Update allowed fields (don't allow changing application_id, created_at, cv_key)
        updatable_fields = [
            'status', 'job_title', 'agency_name', 'company_name',
            'caller', 'caller_method', 'salary', 'perks', 'details', 'tags'
        ]

        for field in updatable_fields:
            if field in body:
                meta[field] = body[field]

        # Update timestamp
        meta['updated_at'] = _utc_now()

        # Save updated metadata
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=meta_key,
            Body=json.dumps(meta, ensure_ascii=False, indent=2).encode('utf-8'),
            ContentType="application/json",
            Metadata={
                'application-id': app_id,
                'updated-at': meta['updated_at']
            }
        )

        logger.info(f"Updated application: {app_id}")

        return _response(200, {
            "application_id": app_id,
            "updated": True,
            "updated_at": meta['updated_at']
        })

    except json.JSONDecodeError as e:
        return _error_response(400, f"Invalid JSON: {str(e)}", "InvalidJSON")
    except ValueError as e:
        return _error_response(400, str(e), "InvalidRequest")
    except ClientError as e:
        return _error_response(500, f"S3 error: {str(e)}", "S3Error")
    except Exception as e:
        logger.exception("Unexpected error in update_application")
        return _error_response(500, f"Internal error: {str(e)}", "InternalError")


def delete_application(event: Dict) -> Dict:
    """
    DELETE /applications/{id}
    Delete application and all associated files
    """
    try:
        path_params = event.get('pathParameters') or {}
        app_id = path_params.get('id')

        if not app_id:
            return _error_response(400, "Missing application ID", "InvalidRequest")

        # Delete all objects in the application folder
        prefix = _app_prefix(app_id)

        # List all objects with this prefix
        objects_to_delete = []
        paginator = s3.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
            for obj in page.get('Contents', []):
                objects_to_delete.append({'Key': obj['Key']})

        if not objects_to_delete:
            return _error_response(404, f"Application not found: {app_id}", "NotFound")

        # Delete all objects
        s3.delete_objects(
            Bucket=BUCKET_NAME,
            Delete={'Objects': objects_to_delete}
        )

        logger.info(f"Deleted application: {app_id} ({len(objects_to_delete)} files)")

        return _response(200, {
            "application_id": app_id,
            "deleted": True,
            "files_deleted": len(objects_to_delete)
        })

    except ValueError as e:
        return _error_response(400, str(e), "InvalidRequest")
    except ClientError as e:
        return _error_response(500, f"S3 error: {str(e)}", "S3Error")
    except Exception as e:
        logger.exception("Unexpected error in delete_application")
        return _error_response(500, f"Internal error: {str(e)}", "InternalError")


def get_cv_upload_url(event: Dict) -> Dict:
    """
    POST /applications/{id}/cv-upload-url
    Get fresh presigned URL for CV upload
    """
    try:
        path_params = event.get('pathParameters') or {}
        app_id = path_params.get('id')

        if not app_id:
            return _error_response(400, "Missing application ID", "InvalidRequest")

        # Verify application exists
        prefix = _app_prefix(app_id)
        meta_key = f"{prefix}meta.json"

        try:
            s3.head_object(Bucket=BUCKET_NAME, Key=meta_key)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return _error_response(404, f"Application not found: {app_id}", "NotFound")
            raise

        # Generate presigned URL for CV upload
        cv_key = f"{prefix}cv.pdf"
        cv_upload_url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                "Bucket": BUCKET_NAME,
                "Key": cv_key,
                "ContentType": "application/pdf"
            },
            ExpiresIn=PRESIGNED_URL_EXPIRY
        )

        logger.info(f"Generated CV upload URL for: {app_id}")

        return _response(200, {
            "application_id": app_id,
            "cv_upload_url": cv_upload_url,
            "cv_upload_url_expires_in": PRESIGNED_URL_EXPIRY,
            "content_type": "application/pdf",
            "max_size_bytes": MAX_CV_SIZE
        })

    except ValueError as e:
        return _error_response(400, str(e), "InvalidRequest")
    except ClientError as e:
        return _error_response(500, f"S3 error: {str(e)}", "S3Error")
    except Exception as e:
        logger.exception("Unexpected error in get_cv_upload_url")
        return _error_response(500, f"Internal error: {str(e)}", "InternalError")


# ============================================================================
# RECRUITER SUBMISSION FUNCTIONS
# ============================================================================

def create_recruiter_submission(event: Dict) -> Dict:
    """
    POST /recruiter-submissions
    Create new recruiter submission with comprehensive input validation
    """
    try:
        body = json.loads(event.get('body') or '{}')

        # ========== INPUT VALIDATION ==========
        # Validate recruiter information
        recruiter_name = body.get("recruiter", {}).get("name", "")
        recruiter_email = body.get("recruiter", {}).get("email", "")
        recruiter_phone = body.get("recruiter", {}).get("phone", "")
        recruiter_agency = body.get("recruiter", {}).get("agency", "")

        valid, error = validate_string(recruiter_name, 100, "Recruiter name")
        if not valid:
            return _error_response(400, error, "ValidationError", event=event)

        valid, error = validate_email(recruiter_email)
        if not valid:
            return _error_response(400, error, "ValidationError", event=event)

        valid, error = validate_phone(recruiter_phone)
        if not valid:
            return _error_response(400, error, "ValidationError", event=event)

        valid, error = validate_string(recruiter_agency, 200, "Agency", required=False)
        if not valid:
            return _error_response(400, error, "ValidationError", event=event)

        # Validate job information
        job_title = body.get("job", {}).get("title", "")
        job_company = body.get("job", {}).get("company", "")
        job_requirements = body.get("job", {}).get("requirements", "")
        job_description = body.get("job", {}).get("description", "")

        valid, error = validate_string(job_title, 200, "Job title")
        if not valid:
            return _error_response(400, error, "ValidationError", event=event)

        valid, error = validate_string(job_company, 200, "Company name")
        if not valid:
            return _error_response(400, error, "ValidationError", event=event)

        valid, error = validate_string(job_requirements, 2000, "Requirements")
        if not valid:
            return _error_response(400, error, "ValidationError", event=event)

        valid, error = validate_string(job_description, 5000, "Description", required=False)
        if not valid:
            return _error_response(400, error, "ValidationError", event=event)

        # Validate salary
        salary_min = body.get("job", {}).get("salary_min", 0)
        salary_max = body.get("job", {}).get("salary_max", 0)

        if not isinstance(salary_min, (int, float)) or salary_min < 0:
            return _error_response(400, "salary_min must be a non-negative number", "ValidationError", event=event)

        if not isinstance(salary_max, (int, float)) or salary_max < 0:
            return _error_response(400, "salary_max must be a non-negative number", "ValidationError", event=event)

        if salary_min > 0 and salary_max > 0 and salary_min > salary_max:
            return _error_response(400, "salary_min cannot exceed salary_max", "ValidationError", event=event)

        # Validate currency
        valid_currencies = ['MYR', 'USD', 'SGD', 'EUR', 'GBP', 'AUD', 'NZD']
        currency = body.get("job", {}).get("currency", "MYR")
        if currency not in valid_currencies:
            return _error_response(400, f"Invalid currency. Must be one of: {', '.join(valid_currencies)}", "ValidationError", event=event)

        # Validate skills (array of strings)
        skills = body.get("job", {}).get("skills", [])
        if not isinstance(skills, list):
            return _error_response(400, "skills must be an array", "ValidationError", event=event)

        if len(skills) > 50:
            return _error_response(400, "Maximum 50 skills allowed", "ValidationError", event=event)

        validated_skills = []
        for skill in skills:
            if not isinstance(skill, str):
                continue
            skill = skill.strip()
            if len(skill) > 100:
                return _error_response(400, "Each skill must be max 100 characters", "ValidationError", event=event)
            if skill:
                validated_skills.append(skill)

        # ========== CREATE SUBMISSION ==========
        # Generate submission ID
        rec_id = _generate_rec_id()
        prefix = _rec_prefix(rec_id)

        # Build metadata with validated data
        meta = {
            "submission_id": rec_id,
            "type": "recruiter_submission",
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "status": "new",  # new, contacted, cv_sent, closed
            "recruiter": {
                "name": recruiter_name,
                "email": recruiter_email,
                "phone": recruiter_phone,
                "agency": recruiter_agency
            },
            "job": {
                "title": job_title,
                "company": job_company,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "currency": currency,
                "requirements": job_requirements,
                "skills": validated_skills,
                "description": job_description
            },
            "files": {
                "job_description": f"{prefix}jd.pdf",
                "customized_cv": None
            },
            "admin_notes": "",
            "contact_history": []
        }

        # Save metadata to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=f"{prefix}meta.json",
            Body=json.dumps(meta, ensure_ascii=False, indent=2).encode('utf-8'),
            ContentType="application/json",
            Metadata={
                'submission-id': rec_id,
                'created-at': meta['created_at']
            }
        )

        # Generate presigned URL for JD upload (10 min expiry)
        jd_upload_url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                "Bucket": BUCKET_NAME,
                "Key": meta["files"]["job_description"],
                "ContentType": "application/pdf"
            },
            ExpiresIn=UPLOAD_URL_EXPIRY
        )

        logger.info(f"Created recruiter submission: {rec_id}")

        # Send WhatsApp notification (non-blocking, failures don't affect submission)
        whatsapp_status = "disabled"
        if WHATSAPP_AVAILABLE and is_whatsapp_enabled():
            try:
                # Note: CV will be uploaded later via presigned URL
                # WhatsApp notification will be sent without CV initially
                success, message = send_application_notification(meta, cv_info=None)
                if success:
                    whatsapp_status = "sent"
                    logger.info(f"WhatsApp notification sent: {message}")
                else:
                    whatsapp_status = "failed"
                    logger.warning(f"WhatsApp notification failed: {message}")
            except Exception as e:
                whatsapp_status = "error"
                logger.exception(f"Error sending WhatsApp notification: {str(e)}")

        return _response(200, {
            "submission_id": rec_id,
            "jd_upload_url": jd_upload_url,
            "jd_upload_url_expires_in": UPLOAD_URL_EXPIRY,
            "created_at": meta["created_at"],
            "whatsapp_notification": whatsapp_status
        }, event=event)

    except json.JSONDecodeError as e:
        return _error_response(400, f"Invalid JSON: {str(e)}", "InvalidJSON")
    except ClientError as e:
        return _error_response(500, f"S3 error: {str(e)}", "S3Error")
    except Exception as e:
        logger.exception("Unexpected error in create_recruiter_submission")
        return _error_response(500, f"Internal error: {str(e)}", "InternalError")


def list_recruiter_submissions(event: Dict) -> Dict:
    """
    GET /recruiter-submissions
    List all recruiter submissions with optional filters
    """
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        status_filter = query_params.get('status')
        limit = min(int(query_params.get('limit', '100')), 1000)

        submissions = []

        logger.info(f"Listing recruiter submissions from bucket: {BUCKET_NAME}")

        # List recruiters prefix
        paginator = s3.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(
            Bucket=BUCKET_NAME,
            Prefix='recruiters/',
            Delimiter='/'
        )

        # Get all year folders
        years = []
        for page in page_iterator:
            for prefix in page.get('CommonPrefixes', []):
                year_prefix = prefix['Prefix']
                years.append(year_prefix)

        # For each year, list submissions
        for year_prefix in years:
            rec_paginator = s3.get_paginator('list_objects_v2')
            rec_page_iterator = rec_paginator.paginate(
                Bucket=BUCKET_NAME,
                Prefix=year_prefix,
                Delimiter='/'
            )

            for page in rec_page_iterator:
                for rec_prefix in page.get('CommonPrefixes', []):
                    rec_folder = rec_prefix['Prefix']
                    meta_key = f"{rec_folder}meta.json"

                    try:
                        # Get meta.json for each submission
                        obj = s3.get_object(Bucket=BUCKET_NAME, Key=meta_key)
                        meta = json.loads(obj['Body'].read().decode('utf-8'))

                        # Apply status filter if provided
                        if status_filter and meta.get('status') != status_filter:
                            continue

                        # Add summary info
                        submissions.append({
                            "submission_id": meta.get("submission_id"),
                            "created_at": meta.get("created_at"),
                            "updated_at": meta.get("updated_at"),
                            "status": meta.get("status"),
                            "recruiter_name": meta.get("recruiter", {}).get("name"),
                            "recruiter_email": meta.get("recruiter", {}).get("email"),
                            "job_title": meta.get("job", {}).get("title"),
                            "company": meta.get("job", {}).get("company"),
                            "salary_max": meta.get("job", {}).get("salary_max")
                        })

                        # Limit results
                        if len(submissions) >= limit:
                            break

                    except ClientError as e:
                        logger.warning(f"Could not read {meta_key}: {str(e)}")
                        continue

                if len(submissions) >= limit:
                    break

            if len(submissions) >= limit:
                break

        # Sort by created_at descending (newest first)
        submissions.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        logger.info(f"Found {len(submissions)} recruiter submissions")

        return _response(200, {
            "submissions": submissions,
            "count": len(submissions),
            "filters": {
                "status": status_filter,
                "limit": limit
            }
        })

    except ClientError as e:
        return _error_response(500, f"S3 error: {str(e)}", "S3Error")
    except Exception as e:
        logger.exception("Unexpected error in list_recruiter_submissions")
        return _error_response(500, f"Internal error: {str(e)}", "InternalError")


def get_recruiter_submission(event: Dict) -> Dict:
    """
    GET /recruiter-submissions/{id}
    Get single recruiter submission with download URLs
    Sanitizes admin-only data for non-admin users
    """
    try:
        path_params = event.get('pathParameters') or {}
        rec_id = path_params.get('id')

        if not rec_id:
            return _error_response(400, "Missing submission ID", "InvalidRequest", event=event)

        # Validate ID format to prevent path traversal
        if not validate_id_format(rec_id, 'rec'):
            return _error_response(400, "Invalid submission ID format", "ValidationError", event=event)

        # Get metadata
        prefix = _rec_prefix(rec_id)
        meta_key = f"{prefix}meta.json"

        try:
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=meta_key)
            meta = json.loads(obj['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return _error_response(404, f"Submission not found: {rec_id}", "NotFound", event=event)
            raise

        # Generate presigned download URLs (5 min expiry)
        jd_key = meta.get("files", {}).get("job_description")
        cv_key = meta.get("files", {}).get("customized_cv")

        jd_download_url = None
        cv_download_url = None

        if jd_key:
            try:
                s3.head_object(Bucket=BUCKET_NAME, Key=jd_key)
                jd_download_url = s3.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={"Bucket": BUCKET_NAME, "Key": jd_key},
                    ExpiresIn=DOWNLOAD_URL_EXPIRY
                )
            except ClientError:
                logger.warning(f"JD not found for {rec_id}: {jd_key}")

        if cv_key:
            try:
                s3.head_object(Bucket=BUCKET_NAME, Key=cv_key)
                cv_download_url = s3.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={"Bucket": BUCKET_NAME, "Key": cv_key},
                    ExpiresIn=DOWNLOAD_URL_EXPIRY
                )
            except ClientError:
                logger.warning(f"Custom CV not found for {rec_id}: {cv_key}")

        meta["jd_download_url"] = jd_download_url
        meta["cv_download_url"] = cv_download_url
        meta["download_url_expires_in"] = DOWNLOAD_URL_EXPIRY

        # Check if user is admin
        user = event.get('user', {})
        user_is_admin = is_admin(user)

        # Sanitize response for non-admin users
        if not user_is_admin:
            meta = sanitize_submission_for_recruiter(meta)
            logger.info(f"Retrieved recruiter submission (sanitized): {rec_id}")
        else:
            logger.info(f"Retrieved recruiter submission (full): {rec_id}")

        return _response(200, meta, event=event)

    except ValueError as e:
        return _error_response(400, str(e), "InvalidRequest")
    except ClientError as e:
        return _error_response(500, f"S3 error: {str(e)}", "S3Error")
    except Exception as e:
        logger.exception("Unexpected error in get_recruiter_submission")
        return _error_response(500, f"Internal error: {str(e)}", "InternalError")


def update_recruiter_status(event: Dict) -> Dict:
    """
    PUT /recruiter-submissions/{id}/status
    Update submission status and add to contact history
    """
    try:
        path_params = event.get('pathParameters') or {}
        rec_id = path_params.get('id')

        if not rec_id:
            return _error_response(400, "Missing submission ID", "InvalidRequest")

        body = json.loads(event.get('body') or '{}')
        new_status = body.get('status')
        contact_note = body.get('note', '')

        if not new_status:
            return _error_response(400, "Missing status field", "InvalidRequest")

        # Get existing metadata
        prefix = _rec_prefix(rec_id)
        meta_key = f"{prefix}meta.json"

        try:
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=meta_key)
            meta = json.loads(obj['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return _error_response(404, f"Submission not found: {rec_id}", "NotFound")
            raise

        # Update status
        old_status = meta.get('status')
        meta['status'] = new_status
        meta['updated_at'] = _utc_now()

        # Add to contact history if status changed
        if old_status != new_status:
            if 'contact_history' not in meta:
                meta['contact_history'] = []

            meta['contact_history'].append({
                "date": _utc_now(),
                "old_status": old_status,
                "new_status": new_status,
                "note": contact_note
            })

        # Save updated metadata
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=meta_key,
            Body=json.dumps(meta, ensure_ascii=False, indent=2).encode('utf-8'),
            ContentType="application/json",
            Metadata={
                'submission-id': rec_id,
                'updated-at': meta['updated_at']
            }
        )

        logger.info(f"Updated status for {rec_id}: {old_status} -> {new_status}")

        return _response(200, {
            "submission_id": rec_id,
            "updated": True,
            "old_status": old_status,
            "new_status": new_status,
            "updated_at": meta['updated_at']
        })

    except json.JSONDecodeError as e:
        return _error_response(400, f"Invalid JSON: {str(e)}", "InvalidJSON")
    except ValueError as e:
        return _error_response(400, str(e), "InvalidRequest")
    except ClientError as e:
        return _error_response(500, f"S3 error: {str(e)}", "S3Error")
    except Exception as e:
        logger.exception("Unexpected error in update_recruiter_status")
        return _error_response(500, f"Internal error: {str(e)}", "InternalError")


def update_recruiter_notes(event: Dict) -> Dict:
    """
    PUT /recruiter-submissions/{id}/notes
    Update admin notes for submission
    """
    try:
        path_params = event.get('pathParameters') or {}
        rec_id = path_params.get('id')

        if not rec_id:
            return _error_response(400, "Missing submission ID", "InvalidRequest")

        body = json.loads(event.get('body') or '{}')
        notes = body.get('notes', '')

        # Get existing metadata
        prefix = _rec_prefix(rec_id)
        meta_key = f"{prefix}meta.json"

        try:
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=meta_key)
            meta = json.loads(obj['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return _error_response(404, f"Submission not found: {rec_id}", "NotFound")
            raise

        # Update notes
        meta['admin_notes'] = notes
        meta['updated_at'] = _utc_now()

        # Save updated metadata
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=meta_key,
            Body=json.dumps(meta, ensure_ascii=False, indent=2).encode('utf-8'),
            ContentType="application/json"
        )

        logger.info(f"Updated notes for {rec_id}")

        return _response(200, {
            "submission_id": rec_id,
            "updated": True,
            "updated_at": meta['updated_at']
        })

    except json.JSONDecodeError as e:
        return _error_response(400, f"Invalid JSON: {str(e)}", "InvalidJSON")
    except ValueError as e:
        return _error_response(400, str(e), "InvalidRequest")
    except ClientError as e:
        return _error_response(500, f"S3 error: {str(e)}", "S3Error")
    except Exception as e:
        logger.exception("Unexpected error in update_recruiter_notes")
        return _error_response(500, f"Internal error: {str(e)}", "InternalError")


def upload_custom_cv(event: Dict) -> Dict:
    """
    POST /recruiter-submissions/{id}/cv-upload
    Get presigned URL for uploading customized CV
    """
    try:
        path_params = event.get('pathParameters') or {}
        rec_id = path_params.get('id')

        if not rec_id:
            return _error_response(400, "Missing submission ID", "InvalidRequest")

        # Verify submission exists
        prefix = _rec_prefix(rec_id)
        meta_key = f"{prefix}meta.json"

        try:
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=meta_key)
            meta = json.loads(obj['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return _error_response(404, f"Submission not found: {rec_id}", "NotFound")
            raise

        # Generate presigned URL for custom CV upload
        cv_key = f"{prefix}cv_custom.pdf"
        cv_upload_url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                "Bucket": BUCKET_NAME,
                "Key": cv_key,
                "ContentType": "application/pdf"
            },
            ExpiresIn=PRESIGNED_URL_EXPIRY
        )

        # Update metadata with CV key
        meta['files']['customized_cv'] = cv_key
        meta['updated_at'] = _utc_now()

        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=meta_key,
            Body=json.dumps(meta, ensure_ascii=False, indent=2).encode('utf-8'),
            ContentType="application/json"
        )

        logger.info(f"Generated custom CV upload URL for: {rec_id}")

        return _response(200, {
            "submission_id": rec_id,
            "cv_upload_url": cv_upload_url,
            "cv_upload_url_expires_in": PRESIGNED_URL_EXPIRY,
            "content_type": "application/pdf",
            "max_size_bytes": MAX_CV_SIZE
        })

    except ValueError as e:
        return _error_response(400, str(e), "InvalidRequest")
    except ClientError as e:
        return _error_response(500, f"S3 error: {str(e)}", "S3Error")
    except Exception as e:
        logger.exception("Unexpected error in upload_custom_cv")
        return _error_response(500, f"Internal error: {str(e)}", "InternalError")


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    Main Lambda handler with authentication and security controls
    Routes requests to appropriate function
    """
    # Sanitize event for logging (remove PII and tokens)
    logger.info(f"Event: {json.dumps(sanitize_event_for_logging(event))}")

    # Handle OPTIONS preflight requests
    method = event.get('requestContext', {}).get('http', {}).get('method') or event.get('httpMethod')
    if method == 'OPTIONS':
        return _response(200, {'message': 'OK'}, event=event)

    # Get path and method
    path = event.get('requestContext', {}).get('http', {}).get('path') or event.get('path', '')
    path = path.rstrip('/')

    # Strip stage name from path (e.g., /prod/applications -> /applications)
    stage = event.get('requestContext', {}).get('stage', '')
    if stage and path.startswith(f'/{stage}'):
        path = path[len(stage) + 1:]  # Remove /stage prefix
        if not path:
            path = '/'

    # Get client IP for rate limiting
    client_ip = event.get('requestContext', {}).get('http', {}).get('sourceIp', '')
    logger.info(f"Request: {method} {path} from {client_ip}")

    # Rate limiting for public submission endpoint
    if method == 'POST' and path == '/recruiter-submissions':
        allowed, error = check_rate_limit(client_ip, limit=5, window=300)  # 5 per 5 minutes
        if not allowed:
            return _error_response(429, error, "RateLimitExceeded", event=event)

    # Authentication and Authorization
    # Public endpoint: POST /recruiter-submissions (recruiter form submission)
    # All other endpoints require authentication
    user = None
    requires_auth = not (method == 'POST' and path == '/recruiter-submissions')

    if requires_auth:
        try:
            user = validate_token(event)
            event['user'] = user  # Add user context to event
            logger.info(f"Authenticated user: {user.get('email', user.get('sub'))}")
        except Exception as e:
            logger.warning(f"Authentication failed: {str(e)}")
            return _error_response(401, str(e), "Unauthorized", event=event)

    # Check if user is admin for admin-only endpoints
    admin_endpoints = [
        ('/recruiter-submissions', 'GET'),  # List all submissions
        ('/recruiter-submissions/', 'GET'),  # Get submission details (starts with)
        ('/status', 'PUT'),  # Update status (ends with)
        ('/notes', 'PUT'),  # Update notes (ends with)
        ('/cv-upload', 'POST'),  # Upload CV (ends with)
        ('/applications', 'GET'),  # List applications
        ('/applications', 'POST'),  # Create application
        ('/applications/', 'GET'),  # Get application (starts with)
        ('/applications/', 'PUT'),  # Update application (starts with)
        ('/applications/', 'DELETE'),  # Delete application (starts with)
        ('/cv-upload-url', 'POST')  # CV upload URL (ends with)
    ]

    is_admin_endpoint = False
    for endpoint_path, endpoint_method in admin_endpoints:
        if endpoint_method == method:
            if endpoint_path.endswith('/') and path.startswith(endpoint_path):
                is_admin_endpoint = True
                break
            elif path.endswith(endpoint_path):
                is_admin_endpoint = True
                break
            elif path == endpoint_path:
                is_admin_endpoint = True
                break

    if is_admin_endpoint and user and not is_admin(user):
        logger.warning(f"Access denied for non-admin user: {user.get('email', user.get('sub'))}")
        return _error_response(403, "Admin access required", "Forbidden", event=event)

    # Route to appropriate handler
    try:
        # ========== RECRUITER SUBMISSION ENDPOINTS ==========
        # POST /recruiter-submissions - Create submission
        if method == 'POST' and path == '/recruiter-submissions':
            return create_recruiter_submission(event)

        # GET /recruiter-submissions - List all submissions
        elif method == 'GET' and path == '/recruiter-submissions':
            return list_recruiter_submissions(event)

        # GET /recruiter-submissions/{id} - Get one submission
        elif method == 'GET' and path.startswith('/recruiter-submissions/') and not path.endswith(('/status', '/notes', '/cv-upload')):
            return get_recruiter_submission(event)

        # PUT /recruiter-submissions/{id}/status - Update status
        elif method == 'PUT' and path.endswith('/status'):
            return update_recruiter_status(event)

        # PUT /recruiter-submissions/{id}/notes - Update notes
        elif method == 'PUT' and path.endswith('/notes'):
            return update_recruiter_notes(event)

        # POST /recruiter-submissions/{id}/cv-upload - Upload custom CV
        elif method == 'POST' and path.startswith('/recruiter-submissions/') and path.endswith('/cv-upload'):
            return upload_custom_cv(event)

        # ========== JOB APPLICATION ENDPOINTS ==========
        # POST /applications - Create
        elif method == 'POST' and path == '/applications':
            return create_application(event)

        # GET /applications - List
        elif method == 'GET' and path == '/applications':
            return list_applications(event)

        # GET /applications/{id} - Get one
        elif method == 'GET' and path.startswith('/applications/') and not path.endswith('/cv-upload-url'):
            return get_application(event)

        # PUT /applications/{id} - Update
        elif method == 'PUT' and path.startswith('/applications/'):
            return update_application(event)

        # DELETE /applications/{id} - Delete
        elif method == 'DELETE' and path.startswith('/applications/'):
            return delete_application(event)

        # POST /applications/{id}/cv-upload-url - Get upload URL
        elif method == 'POST' and path.endswith('/cv-upload-url'):
            return get_cv_upload_url(event)

        else:
            return _error_response(404, f"Endpoint not found: {method} {path}", "NotFound")

    except Exception as e:
        logger.exception("Unexpected error in lambda_handler")
        return _error_response(500, f"Internal server error: {str(e)}", "InternalError")
