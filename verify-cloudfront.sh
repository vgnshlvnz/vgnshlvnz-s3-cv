#!/bin/bash
# CloudFront Configuration Verification Script
# This script verifies that CloudFront is properly configured for cv.vgnshlv.nz

set -e

echo "========================================"
echo "CloudFront Configuration Verification"
echo "========================================"
echo ""

DISTRIBUTION_ID="E1XWXVYFO71217"
EXPECTED_DOMAIN="cv.vgnshlv.nz"
EXPECTED_CERT_ARN="arn:aws:acm:us-east-1:460742884565:certificate/eca0af92-5e9e-4e06-a658-ca38bfa5b8c5"

echo "Distribution ID: $DISTRIBUTION_ID"
echo ""

# Get CloudFront distribution configuration
echo "[1/6] Fetching CloudFront distribution configuration..."
CONFIG=$(aws cloudfront get-distribution --id "$DISTRIBUTION_ID" --query 'Distribution.DistributionConfig' 2>&1)

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Failed to fetch CloudFront configuration"
    echo "Make sure AWS CLI is configured and you have permissions"
    exit 1
fi

echo "✅ Configuration fetched successfully"
echo ""

# Check 1: Alternate Domain Names (CNAMEs)
echo "[2/6] Checking Alternate Domain Names (CNAMEs)..."
ALIASES=$(echo "$CONFIG" | jq -r '.Aliases.Items[]' 2>/dev/null || echo "")

if echo "$ALIASES" | grep -q "$EXPECTED_DOMAIN"; then
    echo "✅ CNAME '$EXPECTED_DOMAIN' is configured"
else
    echo "❌ WARNING: CNAME '$EXPECTED_DOMAIN' NOT found"
    echo "   Current CNAMEs:"
    echo "$ALIASES" | sed 's/^/   - /'
    echo ""
    echo "   FIX: Add alternate domain name in CloudFront:"
    echo "   aws cloudfront get-distribution-config --id $DISTRIBUTION_ID > dist-config.json"
    echo "   # Edit dist-config.json to add '$EXPECTED_DOMAIN' to Aliases.Items"
    echo "   aws cloudfront update-distribution --id $DISTRIBUTION_ID --if-match <ETag> --distribution-config file://dist-config.json"
fi
echo ""

# Check 2: SSL Certificate
echo "[3/6] Checking SSL Certificate configuration..."
CERT_ARN=$(echo "$CONFIG" | jq -r '.ViewerCertificate.ACMCertificateArn // empty' 2>/dev/null)
SSL_METHOD=$(echo "$CONFIG" | jq -r '.ViewerCertificate.SSLSupportMethod // empty' 2>/dev/null)

if [ "$CERT_ARN" == "$EXPECTED_CERT_ARN" ]; then
    echo "✅ Correct ACM certificate attached"
    echo "   ARN: $CERT_ARN"
else
    echo "❌ WARNING: Certificate mismatch"
    echo "   Expected: $EXPECTED_CERT_ARN"
    echo "   Found:    $CERT_ARN"
fi

if [ "$SSL_METHOD" == "sni-only" ]; then
    echo "✅ SSL method: sni-only (recommended, no extra cost)"
else
    echo "⚠️  SSL method: $SSL_METHOD"
    echo "   Consider using 'sni-only' to avoid extra charges"
fi
echo ""

# Check 3: Origin Configuration
echo "[4/6] Checking Origin configuration..."
ORIGIN_DOMAIN=$(echo "$CONFIG" | jq -r '.Origins.Items[0].DomainName' 2>/dev/null)
EXPECTED_ORIGIN="vgnshlvnz-portfolio.s3-website.ap-southeast-5.amazonaws.com"

if [ "$ORIGIN_DOMAIN" == "$EXPECTED_ORIGIN" ]; then
    echo "✅ Origin correctly points to S3 website endpoint"
    echo "   $ORIGIN_DOMAIN"
else
    echo "⚠️  Origin domain: $ORIGIN_DOMAIN"
    echo "   Expected: $EXPECTED_ORIGIN"
fi
echo ""

# Check 4: Default Root Object
echo "[5/6] Checking Default Root Object..."
DEFAULT_ROOT=$(echo "$CONFIG" | jq -r '.DefaultRootObject // empty' 2>/dev/null)

if [ "$DEFAULT_ROOT" == "index.html" ]; then
    echo "✅ Default root object: index.html"
else
    echo "⚠️  Default root object: '$DEFAULT_ROOT'"
    echo "   Should be 'index.html' for proper homepage routing"
fi
echo ""

# Check 5: Distribution Status
echo "[6/6] Checking Distribution status..."
STATUS=$(aws cloudfront get-distribution --id "$DISTRIBUTION_ID" --query 'Distribution.Status' --output text 2>/dev/null)
ENABLED=$(echo "$CONFIG" | jq -r '.Enabled' 2>/dev/null)

if [ "$STATUS" == "Deployed" ]; then
    echo "✅ Distribution status: Deployed"
else
    echo "⚠️  Distribution status: $STATUS"
    echo "   Wait for status to change to 'Deployed'"
fi

if [ "$ENABLED" == "true" ]; then
    echo "✅ Distribution is enabled"
else
    echo "❌ Distribution is DISABLED"
fi
echo ""

# Check 6: ACM Certificate Status
echo "========================================"
echo "ACM Certificate Verification"
echo "========================================"
echo ""

CERT_STATUS=$(aws acm describe-certificate \
    --certificate-arn "$EXPECTED_CERT_ARN" \
    --region us-east-1 \
    --query 'Certificate.Status' \
    --output text 2>/dev/null)

CERT_DOMAIN=$(aws acm describe-certificate \
    --certificate-arn "$EXPECTED_CERT_ARN" \
    --region us-east-1 \
    --query 'Certificate.DomainName' \
    --output text 2>/dev/null)

echo "Certificate Domain: $CERT_DOMAIN"
echo "Certificate Status: $CERT_STATUS"

if [ "$CERT_STATUS" == "ISSUED" ]; then
    echo "✅ Certificate is ISSUED and ready to use"
elif [ "$CERT_STATUS" == "PENDING_VALIDATION" ]; then
    echo "⏳ Certificate is PENDING_VALIDATION"
    echo ""
    echo "Next steps:"
    echo "1. Add DNS validation CNAME to Cloudflare (see DNS-SETUP.md)"
    echo "2. Wait 5-30 minutes for AWS to validate"
    echo "3. Re-run this script to verify"
    echo ""
    echo "Validation records needed:"
    aws acm describe-certificate \
        --certificate-arn "$EXPECTED_CERT_ARN" \
        --region us-east-1 \
        --query 'Certificate.DomainValidationOptions[0].ResourceRecord' \
        --output table 2>/dev/null
else
    echo "⚠️  Unexpected certificate status: $CERT_STATUS"
fi

echo ""
echo "========================================"
echo "Summary"
echo "========================================"
echo ""

# Count checks
PASSED=0
WARNINGS=0

# Tally results
[ ! -z "$(echo "$ALIASES" | grep "$EXPECTED_DOMAIN")" ] && PASSED=$((PASSED+1)) || WARNINGS=$((WARNINGS+1))
[ "$CERT_ARN" == "$EXPECTED_CERT_ARN" ] && PASSED=$((PASSED+1)) || WARNINGS=$((WARNINGS+1))
[ "$ORIGIN_DOMAIN" == "$EXPECTED_ORIGIN" ] && PASSED=$((PASSED+1)) || WARNINGS=$((WARNINGS+1))
[ "$STATUS" == "Deployed" ] && PASSED=$((PASSED+1)) || WARNINGS=$((WARNINGS+1))
[ "$CERT_STATUS" == "ISSUED" ] && PASSED=$((PASSED+1)) || WARNINGS=$((WARNINGS+1))

echo "✅ Checks passed: $PASSED"
echo "⚠️  Warnings: $WARNINGS"
echo ""

if [ "$CERT_STATUS" != "ISSUED" ]; then
    echo "🔴 ACTION REQUIRED: Complete DNS validation (see DNS-SETUP.md)"
elif [ $WARNINGS -eq 0 ]; then
    echo "🟢 CloudFront is properly configured!"
    echo ""
    echo "Next steps:"
    echo "1. Add DNS CNAME to Cloudflare: cv → d1cda43lowke66.cloudfront.net"
    echo "2. Wait 5-15 minutes for DNS propagation"
    echo "3. Visit https://cv.vgnshlv.nz"
else
    echo "🟡 CloudFront has configuration warnings (see above)"
fi

echo ""
echo "========================================"
