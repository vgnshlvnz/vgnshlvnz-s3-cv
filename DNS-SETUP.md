# DNS Setup Guide for cv.vgnshlv.nz

## Overview
This guide will help you configure DNS records in Cloudflare to enable HTTPS access to your CV portfolio at `https://cv.vgnshlv.nz`.

## Prerequisites
- Cloudflare account with access to `vgnshlv.nz` domain
- CloudFront distribution already deployed (✅ Done)
- ACM SSL certificate issued (✅ Done - awaiting validation)

## Step-by-Step Instructions

### Step 1: Add SSL Certificate Validation Record

This CNAME record proves to AWS that you own the domain and allows AWS to issue the SSL certificate.

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select your domain: `vgnshlv.nz`
3. Go to **DNS** → **Records**
4. Click **Add record**
5. Configure the record:

```
Type:    CNAME
Name:    _09870b99f2b91d081db38b5ac73c4832.cv
Target:  _ae18afce56fdbca76320361b0076a2e8.jkddzztszm.acm-validations.aws.
TTL:     Auto
Proxy:   DNS only (turn OFF orange cloud)
```

**IMPORTANT**:
- The **orange cloud must be OFF** (grey cloud icon) for validation records
- Copy the Name and Target values EXACTLY as shown (including trailing dot)
- This record is temporary and can be deleted after SSL validation completes

6. Click **Save**

### Step 2: Add CV Subdomain CNAME Record

This record points your custom domain to the CloudFront CDN.

1. Still in **DNS** → **Records**, click **Add record**
2. Configure the record:

```
Type:    CNAME
Name:    cv
Target:  d1cda43lowke66.cloudfront.net
TTL:     Auto
Proxy:   Proxied (turn ON orange cloud)
```

**RECOMMENDED**:
- Turn **ON** the orange cloud (Proxied) for:
  - Cloudflare's additional CDN layer
  - DDoS protection
  - Web Application Firewall (if enabled)
  - Cloudflare Analytics

**ALTERNATIVE** (DNS only):
- Turn **OFF** the orange cloud if you want to use only AWS CloudFront
- Faster propagation (no Cloudflare proxy layer)
- Direct AWS→User connection

3. Click **Save**

## Step 3: Verify DNS Propagation

Wait 5-15 minutes for DNS changes to propagate, then verify:

### Check DNS Records
```bash
# Check SSL validation record
dig _09870b99f2b91d081db38b5ac73c4832.cv.vgnshlv.nz CNAME +short

# Expected output:
# _ae18afce56fdbca76320361b0076a2e8.jkddzztszm.acm-validations.aws.

# Check CV subdomain
dig cv.vgnshlv.nz CNAME +short

# Expected output (if proxied through Cloudflare):
# cv.vgnshlv.nz points to Cloudflare IPs

# Expected output (if DNS only):
# d1cda43lowke66.cloudfront.net
```

### Check SSL Certificate Validation

1. Go to [AWS Certificate Manager Console](https://console.aws.amazon.com/acm/home?region=us-east-1)
2. Find certificate for `cv.vgnshlv.nz`
3. Status should change from **Pending validation** → **Issued** (takes 5-30 minutes)

## Step 4: Test Your Site

Once the SSL certificate shows "Issued" status:

1. Open browser: `https://cv.vgnshlv.nz`
2. Verify:
   - Page loads successfully
   - Green padlock icon (valid SSL)
   - No certificate warnings
   - All resources load (CSS, JS, images)

## Troubleshooting

### SSL Certificate Stuck on "Pending Validation"

**Symptoms**: Certificate status doesn't change after 30 minutes

**Solutions**:
1. Verify validation CNAME record exists in Cloudflare DNS
2. Ensure orange cloud is **OFF** for validation record
3. Check for typos in Name or Target fields
4. Wait up to 72 hours (usually completes in 5-30 minutes)
5. Use DNS checker: `dig _09870b99f2b91d081db38b5ac73c4832.cv.vgnshlv.nz CNAME`

### Site Not Loading (404 or Connection Error)

**Symptoms**: `https://cv.vgnshlv.nz` returns error

**Solutions**:
1. Verify CloudFront has "Alternate Domain Names (CNAMEs)" set to `cv.vgnshlv.nz`
2. Ensure CloudFront has SSL certificate attached
3. Check DNS propagation: https://dnschecker.org
4. Wait 10-15 minutes for CloudFront to propagate changes
5. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)

### Mixed Content Warnings

**Symptoms**: Green padlock with warning, some resources don't load

**Solutions**:
1. Verify all `<script>`, `<link>`, `<img>` tags use HTTPS or protocol-relative URLs
2. Check browser console for mixed content errors
3. Update any `http://` references to `https://`

### Cloudflare Proxied vs DNS Only

**Use Proxied (Orange Cloud ON)** if you want:
- Additional CDN layer on top of CloudFront
- Cloudflare DDoS protection
- Cloudflare Analytics
- SSL managed by Cloudflare + AWS

**Use DNS Only (Grey Cloud)** if you want:
- Direct AWS CloudFront→User connection
- Faster initial propagation
- Simplified troubleshooting
- Only AWS services in the chain

## DNS Record Summary

After completion, your Cloudflare DNS should show:

| Type  | Name                                  | Target                                                      | Proxy Status |
|-------|---------------------------------------|-------------------------------------------------------------|--------------|
| CNAME | _09870b99f2b91d081db38b5ac73c4832.cv | _ae18afce56fdbca76320361b0076a2e8.jkddzztszm.acm-validations.aws. | DNS only     |
| CNAME | cv                                    | d1cda43lowke66.cloudfront.net                               | Proxied      |

## Post-Setup Verification Checklist

- [ ] DNS validation CNAME added to Cloudflare
- [ ] CV subdomain CNAME added to Cloudflare
- [ ] DNS propagation verified (5-15 minutes)
- [ ] ACM certificate status changed to "Issued"
- [ ] `https://cv.vgnshlv.nz` loads successfully
- [ ] SSL certificate valid (green padlock)
- [ ] All page resources load correctly
- [ ] No mixed content warnings
- [ ] Test on multiple devices/browsers

## Next Steps

Once DNS is working:
1. Update social media links to use `https://cv.vgnshlv.nz`
2. Add domain to Google Search Console
3. Set up CloudFlare Analytics (if using proxied mode)
4. Consider adding `www.cv.vgnshlv.nz` redirect (optional)

## Support Resources

- **ACM Certificate Manager**: https://console.aws.amazon.com/acm/home?region=us-east-1
- **CloudFront Console**: https://console.aws.amazon.com/cloudfront/v3/home
- **Cloudflare Dashboard**: https://dash.cloudflare.com
- **DNS Propagation Checker**: https://dnschecker.org
- **SSL Certificate Checker**: https://www.ssllabs.com/ssltest/

---

**Created**: November 1, 2025
**Last Updated**: November 1, 2025
**Status**: Ready for DNS configuration
