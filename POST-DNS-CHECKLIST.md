# Post-DNS Verification Checklist

## Overview
Use this checklist after adding DNS records to Cloudflare to verify that your CV portfolio is fully operational at `https://cv.vgnshlv.nz`.

## Prerequisites
- [x] DNS records added to Cloudflare (see DNS-SETUP.md)
- [ ] Waited 5-15 minutes for DNS propagation
- [ ] ACM certificate status changed to "Issued"

---

## Phase 1: DNS Propagation Verification

### 1.1 Check DNS Records

```bash
# Check SSL validation record
dig _09870b99f2b91d081db38b5ac73c4832.cv.vgnshlv.nz CNAME +short
```
**Expected**: `_ae18afce56fdbca76320361b0076a2e8.jkddzztszm.acm-validations.aws.`

- [ ] SSL validation CNAME resolves correctly

```bash
# Check CV subdomain
dig cv.vgnshlv.nz +short
```
**Expected** (if Cloudflare proxied): Cloudflare IP addresses
**Expected** (if DNS only): `d1cda43lowke66.cloudfront.net`

- [ ] CV subdomain resolves correctly

### 1.2 Check Global DNS Propagation

Visit: https://dnschecker.org/#CNAME/cv.vgnshlv.nz

- [ ] DNS propagated in at least 10+ global locations
- [ ] All locations show consistent results

---

## Phase 2: SSL Certificate Verification

### 2.1 Check ACM Certificate Status

```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:460742884565:certificate/eca0af92-5e9e-4e06-a658-ca38bfa5b8c5 \
  --region us-east-1 \
  --query 'Certificate.Status' \
  --output text
```
**Expected**: `ISSUED`

- [ ] Certificate status is "ISSUED"
- [ ] Certificate is not "PENDING_VALIDATION"

### 2.2 Verify Certificate Details

```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:460742884565:certificate/eca0af92-5e9e-4e06-a658-ca38bfa5b8c5 \
  --region us-east-1 \
  --query 'Certificate.{Domain:DomainName,Status:Status,Type:Type}' \
  --output table
```

- [ ] Domain matches: `cv.vgnshlv.nz`
- [ ] Type is: `AMAZON_ISSUED`
- [ ] No errors or warnings

---

## Phase 3: CloudFront Configuration Check

### 3.1 Run Verification Script

```bash
cd /home/agh0ri/vgnshlvnz-s3-bucket
./verify-cloudfront.sh
```

- [ ] All checks pass (🟢)
- [ ] No critical errors (🔴)
- [ ] Warnings addressed (🟡)

### 3.2 Manual CloudFront Checks

Visit CloudFront Console: https://console.aws.amazon.com/cloudfront/v3/home#/distributions/E1XWXVYFO71217

- [ ] Distribution status: "Deployed"
- [ ] Enabled: "Yes"
- [ ] Alternate domain names includes: `cv.vgnshlv.nz`
- [ ] SSL certificate shows: `cv.vgnshlv.nz (eca0af92...)`
- [ ] Last modified time is recent

---

## Phase 4: Website Functionality Testing

### 4.1 Basic Connectivity

```bash
# Test HTTPS connectivity
curl -I https://cv.vgnshlv.nz
```
**Expected**: HTTP/2 200 OK

- [ ] HTTP status code: 200
- [ ] No redirect loops
- [ ] Server header includes: CloudFront

### 4.2 Browser Testing

Open in browser: `https://cv.vgnshlv.nz`

#### Visual Checks
- [ ] Page loads completely (no broken layout)
- [ ] Unix man page theme displays correctly
- [ ] Profile image loads
- [ ] Liberation Mono font renders properly
- [ ] No missing CSS styles

#### Security Checks
- [ ] Green padlock icon in address bar
- [ ] No "Not Secure" warnings
- [ ] Certificate valid (click padlock → Certificate)
- [ ] Issued by: Amazon
- [ ] Valid for: cv.vgnshlv.nz

#### Resource Loading
Open browser DevTools (F12) → Network tab:
- [ ] All CSS files load (200 status)
- [ ] All JS files load (200 status)
- [ ] All images load (200 status)
- [ ] No 403/404 errors
- [ ] No mixed content warnings (HTTP resources on HTTPS page)

#### Interactive Features
- [ ] Smooth scrolling navigation works
- [ ] Experience timeline expands/collapses
- [ ] Skill tabs switch correctly (Technical/Cloud/Tools)
- [ ] Download modal opens when clicking CV button
- [ ] Keyboard shortcut 'D' opens download modal
- [ ] Escape key closes modal
- [ ] PDF and DOCX download links work

### 4.3 Performance Testing

Open DevTools → Network tab → Reload page:
- [ ] Page loads in < 2 seconds
- [ ] First Contentful Paint < 1 second
- [ ] All resources served via HTTPS
- [ ] CloudFront cache headers present

Run Lighthouse audit (DevTools → Lighthouse):
- [ ] Performance score > 90
- [ ] Accessibility score > 90
- [ ] Best Practices score > 90
- [ ] SEO score > 80

### 4.4 Mobile Responsiveness

Test on mobile device or DevTools Device Mode:
- [ ] Responsive layout adapts to mobile
- [ ] Text is readable without zooming
- [ ] Buttons/links are tappable
- [ ] No horizontal scrolling
- [ ] Images scale appropriately

---

## Phase 5: Cross-Browser Compatibility

### Desktop Browsers
- [ ] Chrome/Chromium (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

### Mobile Browsers
- [ ] Chrome Mobile (Android)
- [ ] Safari (iOS)
- [ ] Firefox Mobile

---

## Phase 6: SEO & Meta Tags

### 6.1 Verify Page Metadata

View page source (`Ctrl+U`):

- [ ] `<title>` tag exists and descriptive
- [ ] `<meta name="description">` exists
- [ ] `<meta name="viewport">` for mobile
- [ ] Open Graph tags (og:title, og:description, og:image)
- [ ] Canonical URL points to https://cv.vgnshlv.nz

### 6.2 Structured Data

Test with: https://search.google.com/test/rich-results

- [ ] No errors in structured data (if implemented)
- [ ] Valid JSON-LD schema (if implemented)

---

## Phase 7: Monitoring & Analytics Setup

### 7.1 CloudWatch Metrics (Optional)

Visit CloudWatch: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1

- [ ] CloudFront metrics visible
- [ ] No 4xx/5xx errors
- [ ] Request count > 0

### 7.2 CloudFlare Analytics (If Proxied)

Visit Cloudflare Dashboard → Analytics:

- [ ] Traffic showing for cv.vgnshlv.nz
- [ ] SSL/TLS encryption level: Full
- [ ] No security threats detected

---

## Phase 8: Final Validation

### 8.1 External SSL Checkers

Test at: https://www.ssllabs.com/ssltest/analyze.html?d=cv.vgnshlv.nz

- [ ] Overall rating: A or A+
- [ ] Certificate is trusted
- [ ] TLS 1.2+ supported
- [ ] No weak ciphers

### 8.2 Google Search Console Setup (Optional)

1. Add property: `https://cv.vgnshlv.nz`
2. Verify ownership (DNS TXT record or HTML file)
3. Submit sitemap (if you have one)

- [ ] Property verified in Search Console
- [ ] No security issues reported
- [ ] No manual actions

### 8.3 Social Media Link Testing

Test how your site appears when shared:

- **Facebook Debugger**: https://developers.facebook.com/tools/debug/
- **Twitter Card Validator**: https://cards-dev.twitter.com/validator
- **LinkedIn Post Inspector**: https://www.linkedin.com/post-inspector/

- [ ] Preview image displays correctly
- [ ] Title and description appear
- [ ] No broken meta tags

---

## Phase 9: Cleanup

### 9.1 Optional: Remove SSL Validation Record

After certificate is "Issued", the validation CNAME can be deleted:

```
Type: CNAME
Name: _09870b99f2b91d081db38b5ac73c4832.cv
```

- [ ] SSL validation record removed (optional, doesn't hurt to keep it)

### 9.2 Documentation Updates

- [ ] Update LinkedIn profile with https://cv.vgnshlv.nz
- [ ] Update GitHub profile README
- [ ] Update email signature
- [ ] Update resume/CV with new URL

---

## Troubleshooting Quick Reference

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| 404 Not Found | DNS not propagated | Wait 15 more minutes |
| SSL Certificate Warning | Cert not issued | Check ACM status, verify DNS validation CNAME |
| Mixed Content Warning | HTTP resources on HTTPS | Update all resources to HTTPS |
| Slow page load | Not using CloudFront | Verify CNAME points to CloudFront |
| Redirect loop | Origin misconfigured | Check S3 website endpoint vs REST endpoint |
| 403 Forbidden | Bucket policy wrong | Verify public read access in S3 policy |

---

## Sign-Off Checklist

Before marking as "DONE":

- [ ] ✅ DNS fully propagated globally
- [ ] ✅ SSL certificate issued and valid
- [ ] ✅ CloudFront serving content correctly
- [ ] ✅ Website loads with HTTPS and green padlock
- [ ] ✅ All interactive features work
- [ ] ✅ Tested on multiple browsers/devices
- [ ] ✅ Performance is acceptable (< 2s load time)
- [ ] ✅ No console errors or warnings
- [ ] ✅ SSL Labs rating A or A+
- [ ] ✅ Social media previews work

---

## Next Steps After Verification

1. **Set up monitoring**: CloudWatch alarms for 5xx errors
2. **Enable logging**: S3 access logs + CloudFront logs (optional)
3. **Cost monitoring**: Set up AWS Budgets (see COST-SETUP.md)
4. **Backup**: Download static files, store in GitHub
5. **Job Tracker**: Proceed with deploying job application system

---

**Checklist Version**: 1.0
**Last Updated**: November 1, 2025
**Status**: Ready for use after DNS configuration
