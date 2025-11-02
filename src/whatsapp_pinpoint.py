"""
Amazon Pinpoint WhatsApp Notification Module
Sends job application notifications via AWS Pinpoint WhatsApp channel
"""

import json
import os
import logging
from typing import Dict, Any, Optional, Tuple
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
pinpoint = boto3.client('pinpoint', region_name=os.environ.get('REGION', 'ap-southeast-5'))

# Pinpoint configuration (from environment variables)
PINPOINT_APP_ID = os.environ.get('PINPOINT_APP_ID', '')
PINPOINT_ORIGINATION_NUMBER = os.environ.get('PINPOINT_ORIGINATION_NUMBER', '')
PINPOINT_RECIPIENT_NUMBER = os.environ.get('PINPOINT_RECIPIENT_NUMBER', '')

# Message template names (must be pre-approved in Pinpoint)
TEMPLATE_JOB_APPLICATION = 'job_application_notification'


def is_pinpoint_enabled() -> bool:
    """
    Check if Pinpoint WhatsApp is configured

    Returns:
        True if all required config is present, False otherwise
    """
    if not PINPOINT_APP_ID:
        logger.warning("PINPOINT_APP_ID not configured")
        return False
    if not PINPOINT_ORIGINATION_NUMBER:
        logger.warning("PINPOINT_ORIGINATION_NUMBER not configured")
        return False
    if not PINPOINT_RECIPIENT_NUMBER:
        logger.warning("PINPOINT_RECIPIENT_NUMBER not configured")
        return False
    return True


def format_application_message(submission: Dict[str, Any]) -> str:
    """
    Format job application data into WhatsApp message text
    Note: For Pinpoint with templates, this is used as fallback/preview text

    Args:
        submission: Job application submission data

    Returns:
        Formatted message text
    """
    recruiter = submission.get('recruiter', {})
    job = submission.get('job', {})

    # Build message sections
    lines = [
        "🔔 New Job Application",
        "",
        f"👤 {recruiter.get('name', 'N/A')}",
        f"📧 {recruiter.get('email', 'N/A')}",
    ]

    if recruiter.get('phone'):
        lines.append(f"📞 {recruiter.get('phone')}")

    if recruiter.get('agency'):
        lines.append(f"🏢 {recruiter.get('agency')}")

    lines.extend([
        "",
        f"💼 {job.get('title', 'N/A')} at {job.get('company', 'N/A')}",
    ])

    # Salary range
    salary_min = job.get('salary_min', 0)
    salary_max = job.get('salary_max', 0)
    currency = job.get('currency', 'MYR')

    if salary_min > 0 and salary_max > 0:
        lines.append(f"💰 {currency} {salary_min:,} - {salary_max:,}")
    elif salary_min > 0:
        lines.append(f"💰 {currency} {salary_min:,}+")

    # Skills
    skills = job.get('skills', [])
    if skills:
        skills_str = ', '.join(skills[:5])  # Limit to 5 for SMS-style messages
        if len(skills) > 5:
            skills_str += f" +{len(skills) - 5} more"
        lines.append(f"🔧 {skills_str}")

    # Submission metadata
    submission_id = submission.get('submission_id', 'Unknown')
    lines.append(f"\n📋 {submission_id}")

    return '\n'.join(lines)


def send_whatsapp_message(
    recipient: str,
    message_text: str,
    submission_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Send WhatsApp message via Pinpoint

    Args:
        recipient: Recipient phone number in E.164 format
        message_text: Message content
        submission_id: Optional submission ID for tracking

    Returns:
        Tuple of (success: bool, message_id or error: str)
    """
    try:
        # Prepare message request
        message_request = {
            'Addresses': {
                recipient: {
                    'ChannelType': 'SMS'  # WhatsApp uses SMS channel in Pinpoint
                }
            },
            'MessageConfiguration': {
                'SMSMessage': {
                    'Body': message_text,
                    'MessageType': 'TRANSACTIONAL',  # TRANSACTIONAL or PROMOTIONAL
                    'OriginationNumber': PINPOINT_ORIGINATION_NUMBER
                }
            }
        }

        # Add context if submission_id provided
        if submission_id:
            message_request['Context'] = {
                'submission_id': submission_id
            }

        # Send message
        response = pinpoint.send_messages(
            ApplicationId=PINPOINT_APP_ID,
            MessageRequest=message_request
        )

        # Parse response
        result = response.get('MessageResponse', {}).get('Result', {})
        recipient_result = result.get(recipient, {})

        delivery_status = recipient_result.get('DeliveryStatus')
        message_id = recipient_result.get('MessageId', '')
        status_message = recipient_result.get('StatusMessage', '')

        if delivery_status == 'SUCCESSFUL':
            logger.info(f"Pinpoint message sent successfully: {message_id}")
            return True, message_id
        else:
            logger.error(f"Pinpoint delivery failed: {delivery_status} - {status_message}")
            return False, f"{delivery_status}: {status_message}"

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"Pinpoint API error {error_code}: {error_message}")
        return False, f"{error_code}: {error_message}"

    except Exception as e:
        logger.exception(f"Unexpected error sending Pinpoint message: {str(e)}")
        return False, str(e)


def send_application_notification(
    submission: Dict[str, Any],
    cv_info: Optional[Dict[str, str]] = None
) -> Tuple[bool, str]:
    """
    Send job application notification via Pinpoint WhatsApp

    Args:
        submission: Job application data
        cv_info: Optional dict with 'bucket' and 'key' for CV file (not used in Pinpoint currently)

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        if not is_pinpoint_enabled():
            return False, "Pinpoint WhatsApp not configured"

        # Format message
        message_text = format_application_message(submission)
        submission_id = submission.get('submission_id')

        # Send via Pinpoint
        success, result = send_whatsapp_message(
            recipient=PINPOINT_RECIPIENT_NUMBER,
            message_text=message_text,
            submission_id=submission_id
        )

        if success:
            logger.info(f"WhatsApp notification sent via Pinpoint: {result}")
            return True, f"Sent via Pinpoint: {result}"
        else:
            logger.warning(f"WhatsApp notification failed: {result}")
            return False, result

    except Exception as e:
        logger.exception(f"Error sending WhatsApp notification via Pinpoint: {str(e)}")
        return False, str(e)


def send_template_message(
    recipient: str,
    template_name: str,
    template_data: Dict[str, str],
    submission_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Send WhatsApp message using approved Pinpoint template

    Note: Templates must be created and approved in Pinpoint console first

    Args:
        recipient: Recipient phone number in E.164 format
        template_name: Name of approved template
        template_data: Key-value pairs for template substitution
        submission_id: Optional submission ID for tracking

    Returns:
        Tuple of (success: bool, message_id or error: str)
    """
    try:
        # Prepare template message request
        message_request = {
            'Addresses': {
                recipient: {
                    'ChannelType': 'SMS',
                    'Substitutions': template_data
                }
            },
            'MessageConfiguration': {
                'SMSMessage': {
                    'MessageType': 'TRANSACTIONAL',
                    'OriginationNumber': PINPOINT_ORIGINATION_NUMBER,
                    'TemplateId': template_name
                }
            }
        }

        if submission_id:
            message_request['Context'] = {'submission_id': submission_id}

        # Send message
        response = pinpoint.send_messages(
            ApplicationId=PINPOINT_APP_ID,
            MessageRequest=message_request
        )

        # Parse response
        result = response.get('MessageResponse', {}).get('Result', {})
        recipient_result = result.get(recipient, {})

        delivery_status = recipient_result.get('DeliveryStatus')
        message_id = recipient_result.get('MessageId', '')
        status_message = recipient_result.get('StatusMessage', '')

        if delivery_status == 'SUCCESSFUL':
            logger.info(f"Pinpoint template message sent: {message_id}")
            return True, message_id
        else:
            logger.error(f"Pinpoint template delivery failed: {delivery_status}")
            return False, f"{delivery_status}: {status_message}"

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"Pinpoint template error {error_code}: {error_message}")
        return False, f"{error_code}: {error_message}"

    except Exception as e:
        logger.exception(f"Unexpected error sending template message: {str(e)}")
        return False, str(e)


def get_delivery_metrics(submission_id: str) -> Dict[str, Any]:
    """
    Get delivery metrics for a specific submission from Pinpoint

    Args:
        submission_id: Submission ID to look up

    Returns:
        Dict with delivery metrics (sent, delivered, failed counts)
    """
    try:
        # This would use Pinpoint Analytics API to fetch metrics
        # For now, return placeholder
        return {
            'submission_id': submission_id,
            'messages_sent': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'note': 'Metrics not yet implemented'
        }

    except Exception as e:
        logger.error(f"Error fetching delivery metrics: {str(e)}")
        return {
            'error': str(e)
        }
