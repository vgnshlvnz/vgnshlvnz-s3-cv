"""
S3 File Validator Lambda Function
Validates uploaded files for security (magic bytes, file size, malware)
Triggered by S3 PutObject events
"""

import json
import os
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Tuple

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# AWS clients
s3 = boto3.client('s3')

# Configuration
MAX_CV_SIZE = 10 * 1024 * 1024  # 10MB
MAX_JD_SIZE = 5 * 1024 * 1024   # 5MB

# File type signatures (magic bytes)
FILE_SIGNATURES = {
    'pdf': [
        b'%PDF-',  # PDF header
    ],
    'docx': [
        b'PK\x03\x04',  # ZIP header (DOCX is a ZIP archive)
    ],
    'doc': [
        b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1',  # OLE header
    ]
}

# Suspicious patterns that might indicate malware
SUSPICIOUS_PATTERNS = [
    b'<script',
    b'javascript:',
    b'eval(',
    b'<iframe',
    b'<?php',
    b'<%',
]


def get_file_signature(content: bytes) -> bytes:
    """Get first 16 bytes for signature checking"""
    return content[:16] if len(content) >= 16 else content


def validate_file_signature(content: bytes, expected_extension: str) -> Tuple[bool, str]:
    """
    Validate file has correct magic bytes for its extension

    Args:
        content: File content bytes
        expected_extension: Expected file extension (pdf, docx, doc)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not content:
        return False, "Empty file"

    signature = get_file_signature(content)

    # Get expected signatures for this extension
    expected_sigs = FILE_SIGNATURES.get(expected_extension.lower(), [])
    if not expected_sigs:
        return False, f"Unknown file type: {expected_extension}"

    # Check if content starts with any valid signature
    for sig in expected_sigs:
        if signature.startswith(sig):
            return True, ""

    return False, f"Invalid {expected_extension.upper()} file signature"


def check_file_size(size: int, file_type: str) -> Tuple[bool, str]:
    """
    Check if file size is within limits

    Args:
        size: File size in bytes
        file_type: Type of file (cv or jd)

    Returns:
        Tuple of (is_valid, error_message)
    """
    max_size = MAX_CV_SIZE if 'cv' in file_type.lower() else MAX_JD_SIZE

    if size > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"File too large: {size} bytes (max {max_mb}MB)"

    return True, ""


def scan_for_suspicious_content(content: bytes) -> Tuple[bool, str]:
    """
    Scan file content for suspicious patterns

    Args:
        content: File content bytes

    Returns:
        Tuple of (is_safe, warning_message)
    """
    # Convert to lowercase for case-insensitive matching
    content_lower = content.lower()

    for pattern in SUSPICIOUS_PATTERNS:
        if pattern in content_lower:
            return False, f"Suspicious pattern detected: {pattern.decode('utf-8', errors='ignore')}"

    return True, ""


def validate_pdf(content: bytes) -> Tuple[bool, str]:
    """
    Additional PDF-specific validation

    Args:
        content: PDF file content

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for PDF header
    if not content.startswith(b'%PDF-'):
        return False, "Invalid PDF header"

    # Check for EOF marker
    if b'%%EOF' not in content:
        return False, "PDF missing EOF marker (possibly corrupted)"

    # Check for embedded JavaScript (common in malicious PDFs)
    if b'/JavaScript' in content or b'/JS' in content:
        logger.warning("PDF contains JavaScript")
        # Don't reject, but log for manual review

    # Check for suspicious Actions
    if b'/Launch' in content or b'/SubmitForm' in content:
        logger.warning("PDF contains potentially suspicious actions")

    return True, ""


def validate_docx(content: bytes) -> Tuple[bool, str]:
    """
    Additional DOCX-specific validation

    Args:
        content: DOCX file content

    Returns:
        Tuple of (is_valid, error_message)
    """
    # DOCX is a ZIP file, check ZIP signature
    if not content.startswith(b'PK\x03\x04'):
        return False, "Invalid DOCX/ZIP signature"

    # Check for macros (VBA) which can be dangerous
    if b'vbaProject' in content or b'macros/' in content:
        return False, "DOCX contains macros (not allowed for security)"

    return True, ""


def delete_invalid_file(bucket: str, key: str, reason: str):
    """Delete invalid file from S3 and log reason"""
    try:
        s3.delete_object(Bucket=bucket, Key=key)
        logger.warning(f"Deleted invalid file {key}: {reason}")

        # Tag the metadata file to indicate validation failure
        meta_key = key.rsplit('/', 1)[0] + '/meta.json'
        try:
            # Add validation_failed tag
            s3.put_object_tagging(
                Bucket=bucket,
                Key=meta_key,
                Tagging={
                    'TagSet': [
                        {'Key': 'validation_status', 'Value': 'failed'},
                        {'Key': 'validation_reason', 'Value': reason[:256]}  # Max tag value length
                    ]
                }
            )
        except ClientError:
            pass  # Metadata file might not exist yet

    except ClientError as e:
        logger.error(f"Failed to delete invalid file {key}: {str(e)}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for S3 event-triggered file validation

    Args:
        event: S3 event with file upload details
        context: Lambda context

    Returns:
        Dict with validation results
    """
    logger.info(f"File validation triggered: {json.dumps(event)}")

    results = []

    # Process each S3 record
    for record in event.get('Records', []):
        try:
            # Extract S3 info
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            size = record['s3']['object']['size']

            logger.info(f"Validating file: s3://{bucket}/{key} ({size} bytes)")

            # Determine file type from key
            file_extension = key.split('.')[-1].lower()
            if file_extension not in ['pdf', 'docx', 'doc']:
                delete_invalid_file(bucket, key, f"Invalid extension: {file_extension}")
                results.append({
                    'key': key,
                    'status': 'REJECTED',
                    'reason': f"Invalid file extension: {file_extension}"
                })
                continue

            # Check file size
            file_type = 'cv' if 'cv' in key.lower() else 'jd'
            valid_size, size_error = check_file_size(size, file_type)
            if not valid_size:
                delete_invalid_file(bucket, key, size_error)
                results.append({
                    'key': key,
                    'status': 'REJECTED',
                    'reason': size_error
                })
                continue

            # Download file for content validation
            try:
                response = s3.get_object(Bucket=bucket, Key=key)
                content = response['Body'].read()
            except ClientError as e:
                logger.error(f"Failed to download file {key}: {str(e)}")
                results.append({
                    'key': key,
                    'status': 'ERROR',
                    'reason': f"Download failed: {str(e)}"
                })
                continue

            # Validate file signature (magic bytes)
            valid_sig, sig_error = validate_file_signature(content, file_extension)
            if not valid_sig:
                delete_invalid_file(bucket, key, sig_error)
                results.append({
                    'key': key,
                    'status': 'REJECTED',
                    'reason': sig_error
                })
                continue

            # Scan for suspicious content
            is_safe, suspicious_reason = scan_for_suspicious_content(content)
            if not is_safe:
                delete_invalid_file(bucket, key, f"Suspicious content: {suspicious_reason}")
                results.append({
                    'key': key,
                    'status': 'REJECTED',
                    'reason': suspicious_reason
                })
                continue

            # File-type specific validation
            if file_extension == 'pdf':
                valid_pdf, pdf_error = validate_pdf(content)
                if not valid_pdf:
                    delete_invalid_file(bucket, key, pdf_error)
                    results.append({
                        'key': key,
                        'status': 'REJECTED',
                        'reason': pdf_error
                    })
                    continue

            elif file_extension == 'docx':
                valid_docx, docx_error = validate_docx(content)
                if not valid_docx:
                    delete_invalid_file(bucket, key, docx_error)
                    results.append({
                        'key': key,
                        'status': 'REJECTED',
                        'reason': docx_error
                    })
                    continue

            # File passed all validations
            logger.info(f"File validated successfully: {key}")

            # Tag as validated
            try:
                s3.put_object_tagging(
                    Bucket=bucket,
                    Key=key,
                    Tagging={
                        'TagSet': [
                            {'Key': 'validation_status', 'Value': 'passed'},
                            {'Key': 'validated_at', 'Value': context.request_id}
                        ]
                    }
                )
            except ClientError as e:
                logger.warning(f"Failed to tag validated file: {str(e)}")

            results.append({
                'key': key,
                'status': 'ACCEPTED',
                'reason': 'All validations passed'
            })

        except Exception as e:
            logger.exception(f"Error processing record: {str(e)}")
            results.append({
                'key': record.get('s3', {}).get('object', {}).get('key', 'unknown'),
                'status': 'ERROR',
                'reason': str(e)
            })

    logger.info(f"Validation results: {json.dumps(results)}")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'results': results,
            'total': len(results),
            'accepted': len([r for r in results if r['status'] == 'ACCEPTED']),
            'rejected': len([r for r in results if r['status'] == 'REJECTED']),
            'errors': len([r for r in results if r['status'] == 'ERROR'])
        })
    }
