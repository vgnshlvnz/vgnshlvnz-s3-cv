"""
WhatsApp Business API Notification Module
Sends job application notifications via WhatsApp Cloud API
"""

import json
import os
import logging
from typing import Dict, Any, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
secretsmanager = boto3.client('secretsmanager', region_name=os.environ.get('REGION', 'ap-southeast-5'))
s3 = boto3.client('s3', region_name=os.environ.get('REGION', 'ap-southeast-5'))

# Configuration
WHATSAPP_API_VERSION = 'v20.0'
SECRET_NAME = 'job-tracker-whatsapp'

# Cache for credentials (avoid repeated Secrets Manager calls)
_credentials_cache = None


def get_whatsapp_credentials() -> Dict[str, str]:
    """
    Retrieve WhatsApp credentials from AWS Secrets Manager

    Returns:
        Dict with WHATSAPP_TOKEN, PHONE_NUMBER_ID, RECIPIENT_NUMBER
    """
    global _credentials_cache

    if _credentials_cache:
        return _credentials_cache

    try:
        response = secretsmanager.get_secret_value(SecretId=SECRET_NAME)
        credentials = json.loads(response['SecretString'])

        # Validate required fields
        required_fields = ['WHATSAPP_TOKEN', 'PHONE_NUMBER_ID', 'RECIPIENT_NUMBER']
        missing = [f for f in required_fields if f not in credentials]
        if missing:
            raise ValueError(f"Missing required credentials: {', '.join(missing)}")

        _credentials_cache = credentials
        logger.info("WhatsApp credentials loaded successfully")
        return credentials

    except ClientError as e:
        logger.error(f"Failed to retrieve WhatsApp credentials: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in secret: {str(e)}")
        raise


def generate_presigned_url(bucket: str, key: str, expiry: int = 600) -> str:
    """
    Generate pre-signed S3 URL for CV download

    Args:
        bucket: S3 bucket name
        key: S3 object key
        expiry: URL expiry in seconds (default 10 minutes)

    Returns:
        Pre-signed URL
    """
    try:
        from botocore.config import Config
        from botocore.client import generate_presigned_url

        s3_client = boto3.client(
            's3',
            region_name=os.environ.get('REGION', 'ap-southeast-5'),
            config=Config(signature_version='s3v4')
        )

        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiry
        )

        logger.info(f"Generated presigned URL for {bucket}/{key}")
        return url

    except Exception as e:
        logger.error(f"Failed to generate presigned URL: {str(e)}")
        raise


def send_whatsapp_message(phone_number_id: str, token: str, recipient: str, payload: Dict) -> Tuple[bool, Optional[str]]:
    """
    Send message via WhatsApp Cloud API

    Args:
        phone_number_id: WhatsApp Phone Number ID
        token: WhatsApp access token
        recipient: Recipient phone number in E.164 format
        payload: Message payload

    Returns:
        Tuple of (success: bool, message_id: str or error: str)
    """
    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{phone_number_id}/messages"

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    try:
        request = Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )

        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            message_id = result.get('messages', [{}])[0].get('id')
            logger.info(f"WhatsApp message sent successfully: {message_id}")
            return True, message_id

    except HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"WhatsApp API error {e.code}: {error_body}")
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get('error', {}).get('message', error_body)
        except:
            error_msg = error_body
        return False, error_msg

    except URLError as e:
        logger.error(f"Network error sending WhatsApp message: {str(e)}")
        return False, str(e)

    except Exception as e:
        logger.error(f"Unexpected error sending WhatsApp message: {str(e)}")
        return False, str(e)


def format_application_message(submission: Dict[str, Any]) -> str:
    """
    Format job application data into WhatsApp message text

    Args:
        submission: Job application submission data

    Returns:
        Formatted message text
    """
    recruiter = submission.get('recruiter', {})
    job = submission.get('job', {})

    # Build message sections
    lines = [
        "🔔 *New Job Application Received*",
        "",
        "*Recruiter Information:*",
        f"• Name: {recruiter.get('name', 'N/A')}",
        f"• Email: {recruiter.get('email', 'N/A')}",
    ]

    if recruiter.get('phone'):
        lines.append(f"• Phone: {recruiter.get('phone')}")

    if recruiter.get('agency'):
        lines.append(f"• Agency: {recruiter.get('agency')}")

    lines.extend([
        "",
        "*Job Details:*",
        f"• Title: {job.get('title', 'N/A')}",
        f"• Company: {job.get('company', 'N/A')}",
    ])

    # Salary range
    salary_min = job.get('salary_min', 0)
    salary_max = job.get('salary_max', 0)
    currency = job.get('currency', 'MYR')

    if salary_min > 0 and salary_max > 0:
        lines.append(f"• Salary: {currency} {salary_min:,} - {salary_max:,}")
    elif salary_min > 0:
        lines.append(f"• Salary: {currency} {salary_min:,}+")

    # Skills
    skills = job.get('skills', [])
    if skills:
        skills_str = ', '.join(skills[:10])  # Limit to 10 skills
        if len(skills) > 10:
            skills_str += f" (+{len(skills) - 10} more)"
        lines.append(f"• Skills: {skills_str}")

    # Requirements
    requirements = job.get('requirements', '')
    if requirements:
        # Truncate long requirements
        req_preview = requirements[:200] + '...' if len(requirements) > 200 else requirements
        lines.extend([
            "",
            "*Requirements:*",
            req_preview
        ])

    # Submission metadata
    submission_id = submission.get('submission_id', 'Unknown')
    created_at = submission.get('created_at', 'Unknown')

    lines.extend([
        "",
        f"_Submission ID: {submission_id}_",
        f"_Received: {created_at}_"
    ])

    return '\n'.join(lines)


def send_application_notification(submission: Dict[str, Any], cv_info: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    """
    Send job application notification via WhatsApp

    Args:
        submission: Job application data
        cv_info: Optional dict with 'bucket' and 'key' for CV file

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Get credentials
        credentials = get_whatsapp_credentials()
        phone_number_id = credentials['PHONE_NUMBER_ID']
        token = credentials['WHATSAPP_TOKEN']
        recipient = credentials['RECIPIENT_NUMBER']

        # Format application message
        message_text = format_application_message(submission)

        # Send text message with application details
        text_payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": message_text
            }
        }

        success, result = send_whatsapp_message(phone_number_id, token, recipient, text_payload)

        if not success:
            return False, f"Failed to send text message: {result}"

        text_message_id = result

        # Send CV document if provided
        if cv_info and cv_info.get('bucket') and cv_info.get('key'):
            try:
                # Generate presigned URL for CV
                cv_url = generate_presigned_url(
                    bucket=cv_info['bucket'],
                    key=cv_info['key'],
                    expiry=600  # 10 minutes
                )

                # Extract filename from key
                filename = cv_info['key'].split('/')[-1] if '/' in cv_info['key'] else cv_info['key']
                if not filename:
                    filename = 'CV.pdf'

                # Send document message
                doc_payload = {
                    "messaging_product": "whatsapp",
                    "to": recipient,
                    "type": "document",
                    "document": {
                        "link": cv_url,
                        "filename": filename
                    }
                }

                doc_success, doc_result = send_whatsapp_message(phone_number_id, token, recipient, doc_payload)

                if not doc_success:
                    logger.warning(f"Failed to send CV document: {doc_result}")
                    return True, f"Text sent ({text_message_id}), but CV failed: {doc_result}"

                return True, f"Sent text ({text_message_id}) and document ({doc_result})"

            except Exception as e:
                logger.error(f"Error sending CV document: {str(e)}")
                return True, f"Text sent ({text_message_id}), but CV error: {str(e)}"

        return True, f"Message sent: {text_message_id}"

    except Exception as e:
        logger.exception(f"Error sending WhatsApp notification: {str(e)}")
        return False, str(e)


def is_whatsapp_enabled() -> bool:
    """
    Check if WhatsApp notifications are enabled

    Returns:
        True if enabled, False otherwise
    """
    try:
        get_whatsapp_credentials()
        return True
    except Exception as e:
        logger.warning(f"WhatsApp notifications disabled: {str(e)}")
        return False
