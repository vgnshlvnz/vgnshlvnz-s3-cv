"""
Job Tracker Lambda Function
Handles CRUD operations for job applications stored in S3
"""

import json
import os
import uuid
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
s3 = boto3.client('s3')

# Environment variables
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'vgnshlvnz-job-tracker')
PRESIGNED_URL_EXPIRY = int(os.environ.get('PRESIGNED_URL_EXPIRY', '900'))
REGION = os.environ.get('REGION', 'ap-southeast-5')

# Constants
ALLOWED_CV_TYPES = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
MAX_CV_SIZE = 10 * 1024 * 1024  # 10MB


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


def _response(status_code: int, body: Dict[str, Any], headers: Optional[Dict] = None) -> Dict:
    """Build API Gateway response"""
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    if headers:
        default_headers.update(headers)

    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body, ensure_ascii=False, indent=2)
    }


def _error_response(status_code: int, message: str, error_type: str = 'Error') -> Dict:
    """Build error response"""
    logger.error(f"{error_type}: {message}")
    return _response(status_code, {
        'error': error_type,
        'message': message
    })


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


def lambda_handler(event: Dict, context: Any) -> Dict:
    """
    Main Lambda handler
    Routes requests to appropriate function
    """
    logger.info(f"Event: {json.dumps(event)}")

    # Handle OPTIONS preflight requests
    method = event.get('requestContext', {}).get('http', {}).get('method') or event.get('httpMethod')
    if method == 'OPTIONS':
        return _response(200, {'message': 'OK'})

    # Get path and method
    path = event.get('requestContext', {}).get('http', {}).get('path') or event.get('path', '')
    path = path.rstrip('/')

    # Strip stage name from path (e.g., /prod/applications -> /applications)
    stage = event.get('requestContext', {}).get('stage', '')
    if stage and path.startswith(f'/{stage}'):
        path = path[len(stage) + 1:]  # Remove /stage prefix
        if not path:
            path = '/'

    logger.info(f"Request: {method} {path}")

    # Route to appropriate handler
    try:
        # POST /applications - Create
        if method == 'POST' and path == '/applications':
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
