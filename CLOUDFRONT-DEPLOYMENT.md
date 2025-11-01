# CloudFront Custom Domain Configuration

## Date: November 1, 2025

## Summary
Configured CloudFront distribution to accept cv.vgnshlv.nz as a custom domain with ACM SSL certificate.

## Changes Made

### CloudFront Distribution (E1XWXVYFO71217)

**Before:**
- No alternate domain names (CNAMEs)
- Using CloudFront default certificate
- SSL Support: VIP
- Protocol: TLSv1

**After:**
- Alternate domain: `cv.vgnshlv.nz`
- ACM Certificate: `arn:aws:acm:us-east-1:460742884565:certificate/eca0af92-5e9e-4e06-a658-ca38bfa5b8c5`
- SSL Support: SNI-only (cost-effective)
- Protocol: TLSv1.2_2021 (modern security)

## Configuration Details

```json
{
  "Aliases": {
    "Quantity": 1,
    "Items": ["cv.vgnshlv.nz"]
  },
  "ViewerCertificate": {
    "ACMCertificateArn": "arn:aws:acm:us-east-1:460742884565:certificate/eca0af92-5e9e-4e06-a658-ca38bfa5b8c5",
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021",
    "CertificateSource": "acm"
  }
}
```

## Verification

### DNS Resolution
```bash
$ dig cv.vgnshlv.nz +short
d1cda43lowke66.cloudfront.net.
54.192.116.43
54.192.116.101
54.192.116.137
54.192.116.218
```

### HTTPS Test
```bash
$ curl -I https://cv.vgnshlv.nz
HTTP/2 200
server: AmazonS3
x-cache: Hit from cloudfront
x-amz-cf-id: 5CSY4jOzyTdkh7_ltrf2JrqSvl55rksmCySoOsqRzHpnBBarLP_GDg==
```

### Certificate Validation
```bash
$ aws acm describe-certificate \
    --certificate-arn arn:aws:acm:us-east-1:460742884565:certificate/eca0af92-5e9e-4e06-a658-ca38bfa5b8c5 \
    --region us-east-1

Status: ISSUED
DomainName: cv.vgnshlv.nz
```

## Deployment Timeline

| Time (UTC) | Action | Status |
|------------|--------|--------|
| 10:17 | Retrieved CloudFront configuration | ✅ Complete |
| 10:18 | Verified ACM certificate status | ✅ ISSUED |
| 10:20 | Updated distribution config with custom domain | ✅ Complete |
| 10:22 | CloudFront deployment initiated | ✅ InProgress |
| 10:23 | Tested cv.vgnshlv.nz - HTTP/2 200 | ✅ LIVE |

## Current Production URLs

| Service | URL | Status |
|---------|-----|--------|
| CV Portfolio | https://cv.vgnshlv.nz | 🟢 LIVE |
| CloudFront Direct | https://d1cda43lowke66.cloudfront.net | 🟢 LIVE |
| Pangolin Proxy | https://entry.vgnshlv.nz | 🟢 LIVE |
| Job Tracker API | https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod | 🟢 LIVE |

## Infrastructure Components

### 1. CloudFront Distribution
- **Distribution ID**: E1XWXVYFO71217
- **Domain Name**: d1cda43lowke66.cloudfront.net
- **Custom Domain**: cv.vgnshlv.nz
- **Status**: Deployed
- **Caching**: Enabled
- **Origin**: S3 bucket vgnshlvnz-portfolio

### 2. ACM Certificate (us-east-1)
- **ARN**: arn:aws:acm:us-east-1:460742884565:certificate/eca0af92-5e9e-4e06-a658-ca38bfa5b8c5
- **Domain**: cv.vgnshlv.nz
- **Status**: ISSUED
- **Validation**: DNS validation via Cloudflare

### 3. DNS Configuration
- **Hosted via**: Cloudflare
- **Nameservers**: sydney.ns.cloudflare.com, hal.ns.cloudflare.com
- **CNAME Record**: cv.vgnshlv.nz → d1cda43lowke66.cloudfront.net

### 4. EC2 Instance (Pangolin)
- **Instance ID**: i-085faef7c8eba079c
- **Public IP**: 43.217.104.44
- **Domain**: entry.vgnshlv.nz
- **Services**: Pangolin, Gerbil (WireGuard), Traefik

### 5. Lambda Function (Job Tracker)
- **Function Name**: job-tracker-api
- **Runtime**: Python 3.12
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Code Size**: 4,454 bytes
- **API Endpoints**: 7 CRUD operations

## Security Features

✅ TLS 1.2 minimum (modern security)
✅ SNI-only SSL (cost-effective)
✅ ACM managed certificate (auto-renewal)
✅ HTTPS enforced
✅ CloudFront signed URLs not required (public portfolio)

## Cost Optimization

- **SNI-only SSL**: Free (vs $600/month for dedicated IP)
- **CloudFront**: Pay-as-you-go
- **ACM Certificate**: Free
- **Lambda**: Free tier eligible
- **S3**: Intelligent-Tiering after 30 days

## Troubleshooting

### Issue: 403 Forbidden on cv.vgnshlv.nz
**Root Cause**: CloudFront distribution did not have cv.vgnshlv.nz configured as alternate domain name

**Solution**:
1. Added cv.vgnshlv.nz to Aliases configuration
2. Associated ACM certificate
3. Changed SSL from CloudFront default to ACM certificate
4. Waited for CloudFront deployment (~5 minutes)

**Verification**:
```bash
curl -I https://cv.vgnshlv.nz
# Should return HTTP/2 200
```

## Next Steps (Optional)

1. **Switch to Route53** (if desired):
   - Update nameservers at OnlyDomains.com to AWS Route53
   - Current: Cloudflare (working)
   - Alternative: ns-360.awsdns-45.com, ns-697.awsdns-23.net, etc.

2. **CloudFront Monitoring**:
   - Set up CloudWatch alarms for 4xx/5xx errors
   - Monitor cache hit ratio
   - Track data transfer for cost optimization

3. **Content Invalidation**:
   ```bash
   aws cloudfront create-invalidation \
     --distribution-id E1XWXVYFO71217 \
     --paths "/*"
   ```

## References

- CloudFront Distribution: https://console.aws.amazon.com/cloudfront/v3/home#/distributions/E1XWXVYFO71217
- ACM Certificate: https://console.aws.amazon.com/acm/home?region=us-east-1#/certificates/eca0af92-5e9e-4e06-a658-ca38bfa5b8c5
- S3 Bucket: https://s3.console.aws.amazon.com/s3/buckets/vgnshlvnz-portfolio

---

**Deployment Status**: ✅ Complete
**Last Updated**: 2025-11-01 10:23 UTC
**Deployed By**: Claude Code
