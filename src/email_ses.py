"""
Amazon SES Email Notification Module
Sends job application notifications via AWS SES
"""

import json
import os
import logging
from html import escape as html_escape
from typing import Dict, Any, Optional, Tuple
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS SES client (must use ap-southeast-1 since SES not available in ap-southeast-5)
ses = boto3.client('ses', region_name=os.environ.get('SES_REGION', 'ap-southeast-1'))

# Configuration from environment variables
SES_SENDER_EMAIL = os.environ.get('SES_SENDER_EMAIL', '')
SES_RECIPIENT_EMAIL = os.environ.get('SES_RECIPIENT_EMAIL', '')
SES_REPLY_TO = os.environ.get('SES_REPLY_TO', '')
SES_CHARSET = 'UTF-8'


def is_ses_enabled() -> bool:
    """
    Check if SES email notifications are configured

    Returns:
        True if all required config is present, False otherwise
    """
    if not SES_SENDER_EMAIL:
        logger.warning("SES_SENDER_EMAIL not configured")
        return False
    if not SES_RECIPIENT_EMAIL:
        logger.warning("SES_RECIPIENT_EMAIL not configured")
        return False
    return True


def format_application_email(submission: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Format job application data into email (HTML and plain text)

    Args:
        submission: Job application submission data

    Returns:
        Tuple of (subject, html_body, text_body)
    """
    recruiter = submission.get('recruiter', {})
    job = submission.get('job', {})
    submission_id = submission.get('submission_id', 'Unknown')
    created_at = submission.get('created_at', 'Unknown')

    # Escape all user-controlled data for HTML injection prevention
    # Recruiter data
    recruiter_name = html_escape(recruiter.get('name', 'N/A'))
    recruiter_email = html_escape(recruiter.get('email', 'N/A'))
    recruiter_email_raw = recruiter.get('email', '')  # For mailto: href
    recruiter_phone = html_escape(recruiter.get('phone', 'N/A'))
    recruiter_phone_raw = recruiter.get('phone', '')  # For tel: href
    recruiter_agency = html_escape(recruiter.get('agency', '')) if recruiter.get('agency') else ''

    # Job data
    job_title = html_escape(job.get('title', 'N/A'))
    company = html_escape(job.get('company', 'N/A'))
    requirements = html_escape(job.get('requirements', 'N/A'))
    description = html_escape(job.get('description', 'N/A'))

    # Escape submission metadata
    submission_id_safe = html_escape(submission_id)
    created_at_safe = html_escape(created_at)

    # Build subject line (for email subject, basic escaping is sufficient)
    subject = f"New Job Application: {job_title} at {company} - {submission_id_safe}"

    # Build salary range string (numbers are safe, but escape currency code)
    salary_min = job.get('salary_min', 0)
    salary_max = job.get('salary_max', 0)
    currency = html_escape(job.get('currency', 'MYR'))

    if salary_min > 0 and salary_max > 0:
        salary_str = f"{currency} {salary_min:,} - {salary_max:,}"
    elif salary_min > 0:
        salary_str = f"{currency} {salary_min:,}+"
    else:
        salary_str = "Not specified"

    # Build skills list with HTML escaping
    skills = job.get('skills', [])
    if skills:
        escaped_skills = [html_escape(str(skill)) for skill in skills[:10]]
        skills_str = ', '.join(escaped_skills)
        if len(skills) > 10:
            skills_str += f" (+{len(skills) - 10} more)"
    else:
        skills_str = "Not specified"

    # HTML email body
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Job Application</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Courier New', monospace; background-color: #f5f5f5;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5; padding: 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #2c3e50; color: #ffffff; padding: 25px; border-radius: 8px 8px 0 0;">
                            <h1 style="margin: 0; font-size: 24px; font-weight: normal;">🔔 New Job Application</h1>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding: 30px;">
                            <!-- Recruiter Information -->
                            <h2 style="color: #2c3e50; font-size: 18px; margin: 0 0 15px 0; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px;">👤 Recruiter Information</h2>
                            <table width="100%" cellpadding="5" cellspacing="0" style="margin-bottom: 25px;">
                                <tr>
                                    <td style="color: #7f8c8d; width: 100px;"><strong>Name:</strong></td>
                                    <td style="color: #2c3e50;">{recruiter_name}</td>
                                </tr>
                                <tr>
                                    <td style="color: #7f8c8d;"><strong>Email:</strong></td>
                                    <td style="color: #2c3e50;"><a href="mailto:{recruiter_email_raw}" style="color: #000080; text-decoration: none;">{recruiter_email}</a></td>
                                </tr>
                                <tr>
                                    <td style="color: #7f8c8d;"><strong>Phone:</strong></td>
                                    <td style="color: #2c3e50;"><a href="tel:{recruiter_phone_raw}" style="color: #000080; text-decoration: none;">{recruiter_phone}</a></td>
                                </tr>
                                {f'<tr><td style="color: #7f8c8d;"><strong>Agency:</strong></td><td style="color: #2c3e50;">{recruiter_agency}</td></tr>' if recruiter_agency else ''}
                            </table>

                            <!-- Job Details -->
                            <h2 style="color: #2c3e50; font-size: 18px; margin: 0 0 15px 0; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px;">💼 Job Details</h2>
                            <table width="100%" cellpadding="5" cellspacing="0" style="margin-bottom: 25px;">
                                <tr>
                                    <td style="color: #7f8c8d; width: 100px;"><strong>Position:</strong></td>
                                    <td style="color: #2c3e50; font-weight: bold;">{job_title}</td>
                                </tr>
                                <tr>
                                    <td style="color: #7f8c8d;"><strong>Company:</strong></td>
                                    <td style="color: #2c3e50;">{company}</td>
                                </tr>
                                <tr>
                                    <td style="color: #7f8c8d;"><strong>Salary:</strong></td>
                                    <td style="color: #2c3e50;">{salary_str}</td>
                                </tr>
                                <tr>
                                    <td style="color: #7f8c8d;"><strong>Skills:</strong></td>
                                    <td style="color: #2c3e50;">{skills_str}</td>
                                </tr>
                            </table>

                            {f'''<!-- Requirements -->
                            <h2 style="color: #2c3e50; font-size: 18px; margin: 0 0 15px 0; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px;">📋 Requirements</h2>
                            <p style="color: #34495e; line-height: 1.6; background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin-bottom: 25px;">{requirements}</p>
                            ''' if job.get('requirements') else ''}

                            {f'''<!-- Description -->
                            <h2 style="color: #2c3e50; font-size: 18px; margin: 0 0 15px 0; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px;">📝 Description</h2>
                            <p style="color: #34495e; line-height: 1.6; background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin-bottom: 25px;">{description}</p>
                            ''' if job.get('description') else ''}

                            <!-- Action Button -->
                            <div style="text-align: center; margin: 30px 0;">
                                <a href="https://cv.vgnshlv.nz/recruiter-dashboard.html?highlight={submission_id_safe}" style="background-color: #000080; color: #ffffff; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">📊 View Full Details in Dashboard</a>
                            </div>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #ecf0f1; padding: 20px; border-radius: 0 0 8px 8px; text-align: center;">
                            <p style="margin: 5px 0; color: #7f8c8d; font-size: 12px;"><strong>Submission ID:</strong> {submission_id_safe}</p>
                            <p style="margin: 5px 0; color: #7f8c8d; font-size: 12px;"><strong>Received:</strong> {created_at_safe}</p>
                            <p style="margin: 15px 0 5px 0; color: #95a5a6; font-size: 11px;">Job Tracker System • <a href="https://cv.vgnshlv.nz" style="color: #000080; text-decoration: none;">cv.vgnshlv.nz</a></p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    # Plain text email body (fallback)
    # Note: Text email is less vulnerable to injection, but we use escaped values for consistency
    text_body = f"""
NEW JOB APPLICATION
{'=' * 60}

RECRUITER INFORMATION:
----------------------
Name:    {recruiter_name}
Email:   {recruiter_email}
Phone:   {recruiter_phone}
{f"Agency:  {recruiter_agency}" if recruiter_agency else ''}

JOB DETAILS:
------------
Position: {job_title}
Company:  {company}
Salary:   {salary_str}
Skills:   {skills_str}

{f"REQUIREMENTS:\\n{requirements}\\n" if job.get('requirements') else ''}
{f"DESCRIPTION:\\n{description}\\n" if job.get('description') else ''}

{'=' * 60}
Submission ID: {submission_id_safe}
Received:      {created_at_safe}

View full details: https://cv.vgnshlv.nz/recruiter-dashboard.html?highlight={submission_id_safe}

Job Tracker System - cv.vgnshlv.nz
"""

    return subject, html_body.strip(), text_body.strip()


def send_email(
    recipient: str,
    subject: str,
    html_body: str,
    text_body: str,
    submission_id: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Send email via Amazon SES

    Args:
        recipient: Recipient email address
        subject: Email subject line
        html_body: HTML version of email body
        text_body: Plain text version of email body
        submission_id: Optional submission ID for tracking

    Returns:
        Tuple of (success: bool, message_id or error: str)
    """
    try:
        # Prepare email parameters
        email_params = {
            'Source': SES_SENDER_EMAIL,
            'Destination': {
                'ToAddresses': [recipient]
            },
            'Message': {
                'Subject': {
                    'Data': subject,
                    'Charset': SES_CHARSET
                },
                'Body': {
                    'Text': {
                        'Data': text_body,
                        'Charset': SES_CHARSET
                    },
                    'Html': {
                        'Data': html_body,
                        'Charset': SES_CHARSET
                    }
                }
            }
        }

        # Add Reply-To header if configured
        if SES_REPLY_TO:
            email_params['ReplyToAddresses'] = [SES_REPLY_TO]

        # Send email via SES
        response = ses.send_email(**email_params)

        message_id = response.get('MessageId', '')
        logger.info(f"Email sent successfully via SES: {message_id}")

        if submission_id:
            logger.info(f"Email sent for submission: {submission_id}, MessageId: {message_id}")

        return True, message_id

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"SES API error {error_code}: {error_message}")
        return False, f"{error_code}: {error_message}"

    except Exception as e:
        logger.exception(f"Unexpected error sending email via SES: {str(e)}")
        return False, str(e)


def send_application_notification(
    submission: Dict[str, Any],
    cv_info: Optional[Dict[str, str]] = None
) -> Tuple[bool, str]:
    """
    Send job application notification via SES email

    Args:
        submission: Job application data
        cv_info: Optional dict with 'bucket' and 'key' for CV file (not used in email currently)

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        if not is_ses_enabled():
            return False, "SES email not configured"

        # Format email content
        subject, html_body, text_body = format_application_email(submission)
        submission_id = submission.get('submission_id')

        # Send email
        success, result = send_email(
            recipient=SES_RECIPIENT_EMAIL,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            submission_id=submission_id
        )

        if success:
            logger.info(f"Email notification sent via SES: {result}")
            return True, f"Email sent: {result}"
        else:
            logger.warning(f"Email notification failed: {result}")
            return False, result

    except Exception as e:
        logger.exception(f"Error sending email notification via SES: {str(e)}")
        return False, str(e)


def get_send_quota() -> Dict[str, Any]:
    """
    Get SES sending quota (for monitoring)

    Returns:
        Dict with quota information
    """
    try:
        response = ses.get_send_quota()
        return {
            'max_24_hour_send': response.get('Max24HourSend', 0),
            'max_send_rate': response.get('MaxSendRate', 0),
            'sent_last_24_hours': response.get('SentLast24Hours', 0),
            'remaining_sends': response.get('Max24HourSend', 0) - response.get('SentLast24Hours', 0)
        }
    except Exception as e:
        logger.error(f"Error fetching SES quota: {str(e)}")
        return {'error': str(e)}
