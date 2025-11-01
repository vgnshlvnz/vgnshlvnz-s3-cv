# DNS Migration Summary

## Status: Ready for Nameserver Update

✅ **Route53 Hosted Zone**: Z0802572M24QS5IJ96NJ
✅ **DNS Records Created**: 2 records ready
✅ **New EC2 Instance**: 43.217.104.44 (Pangolin reverse proxy)

---

## Route53 DNS Records (Active after nameserver change)

| Record Name | Type | Value | TTL | Purpose |
|-------------|------|-------|-----|---------|
| entry.vgnshlv.nz | A | 43.217.104.44 | 300 | Pangolin reverse proxy (new EC2) |
| cv.vgnshlv.nz | CNAME | d1cda43lowke66.cloudfront.net | 300 | CV Portfolio (CloudFront CDN) |

---

## OnlyDomains.com Nameserver Configuration

### Update These Nameservers at OnlyDomains.com

**Domain**: vgnshlv.nz

**New Nameservers** (copy all 4):
```
ns-360.awsdns-45.com
ns-697.awsdns-23.net
ns-1560.awsdns-03.co.uk
ns-1058.awsdns-04.org
```

### Steps:
1. Log in to https://www.onlydomains.com
2. Go to Domain Management → vgnshlv.nz
3. Find "Nameservers" section
4. Select "Custom Nameservers"
5. Enter all 4 AWS nameservers above
6. Save changes
7. Wait 1-24 hours for propagation

---

## Infrastructure Summary

### New Pangolin Server (EC2)
- **Instance ID**: i-085faef7c8eba079c
- **Public IP**: 43.217.104.44
- **DNS**: ec2-43-217-104-44.ap-southeast-5.compute.amazonaws.com
- **Type**: t3.micro (free tier)
- **OS**: Ubuntu 22.04 LTS
- **Docker**: 28.5.1 with Compose v2.40.3
- **Files**: /opt/entry (transferred from old server)
- **SSH**: ssh -i ~/.ssh/id_ed25519 ubuntu@43.217.104.44

### CV Portfolio (CloudFront)
- **Distribution ID**: E1XWXVYFO71217
- **CloudFront Domain**: d1cda43lowke66.cloudfront.net
- **Custom Domain**: cv.vgnshlv.nz (after DNS propagation)
- **SSL Certificate**: ISSUED (arn:...eca0af92-5e9e-4e06-a658-ca38bfa5b8c5)
- **Origin**: S3 bucket vgnshlvnz-portfolio

### Job Tracker API
- **Endpoint**: https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod
- **Lambda**: job-tracker-api (needs update to Python 3.12)
- **Storage**: S3 bucket vgnshlvnz-job-tracker

---

## Next Steps After DNS Propagation

### 1. Start Pangolin (Immediate - after nameserver update)

```bash
# SSH into new server
ssh -i ~/.ssh/id_ed25519 ubuntu@43.217.104.44

# Start Pangolin
cd /opt/entry
docker compose up -d

# Check status
docker compose ps
docker compose logs -f
```

### 2. Verify DNS Resolution (After 1-24 hours)

```bash
# Check nameservers
dig vgnshlv.nz NS +short
# Should show: ns-360.awsdns-45.com, etc.

# Check entry subdomain
dig entry.vgnshlv.nz +short
# Should show: 43.217.104.44

# Check cv subdomain
dig cv.vgnshlv.nz +short
# Should show: d1cda43lowke66.cloudfront.net or CloudFront IPs
```

### 3. Test Services

```bash
# Test Pangolin reverse proxy
curl -I https://entry.vgnshlv.nz

# Test CV portfolio
curl -I https://cv.vgnshlv.nz

# Test Job Tracker API
curl https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications
```

### 4. Update SSL Certificates (if needed)

Once DNS propagates, verify SSL certificates are working:
- ✅ cv.vgnshlv.nz should use ACM certificate automatically
- Pangolin may need Let's Encrypt setup (Traefik handles this)

---

## Rollback Plan (If Issues Occur)

If something goes wrong after nameserver change:

1. **Immediate Rollback**: Change nameservers back to OnlyDomains nameservers at onlydomains.com
2. **Wait**: 1-24 hours for propagation back
3. **Services restore**: Old configuration becomes active again

**Before rollback**, check:
- Is it just DNS propagation delay? (wait longer)
- Are Route53 records correct? (fix records instead)
- Is the service itself down? (check EC2/CloudFront)

---

## Monitoring After Migration

### DNS Propagation Status
- **Tool**: https://dnschecker.org
- **Check**: entry.vgnshlv.nz and cv.vgnshlv.nz
- **Expect**: Gradual propagation over 1-24 hours

### Service Health Checks
```bash
# Pangolin health
curl http://43.217.104.44:3001/api/v1/

# CloudFront health
curl -I https://d1cda43lowke66.cloudfront.net

# API health
curl https://riyot36gu9.execute-api.ap-southeast-5.amazonaws.com/prod/applications
```

---

## Important Notes

⚠️ **Before Changing Nameservers**:
- Ensure you don't have other DNS records at OnlyDomains (MX, TXT, etc.)
- If you have email (MX records), add them to Route53 first
- Document any other subdomains that need to be migrated

✅ **After Nameserver Change**:
- Monitor DNS propagation (1-24 hours)
- Test all services once DNS resolves
- Keep old EC2 instance running for 7 days (backup)
- Update any hard-coded IPs in applications

🔐 **Security**:
- Old server password: AlternateF13! (change after migration)
- New server uses SSH key authentication (more secure)
- Update sudo password on new server

---

## Migration Timeline

| Time | Action | Status |
|------|--------|--------|
| Nov 1, 09:00 | Created new EC2 instance | ✅ Complete |
| Nov 1, 09:08 | Transferred /opt/entry files | ✅ Complete |
| Nov 1, 09:09 | Installed Docker 28.5.1 | ✅ Complete |
| Nov 1, 09:15 | Created Route53 DNS records | ✅ Complete |
| Nov 1, 09:21 | Created cv.vgnshlv.nz CNAME | ✅ Complete |
| **Next** | **Update nameservers at OnlyDomains** | ⏳ **Action Required** |
| +1-24h | DNS propagation completes | ⏳ Pending |
| +24h | Start Pangolin on new server | ⏳ Pending |
| +7 days | Terminate old server (if all OK) | ⏳ Pending |

---

## Contact & Support

**AWS Resources**:
- Route53 Console: https://console.aws.amazon.com/route53/v2/hostedzones#ListRecordSets/Z0802572M24QS5IJ96NJ
- EC2 Console: https://console.aws.amazon.com/ec2/v2/home?region=ap-southeast-5#Instances:instanceId=i-085faef7c8eba079c
- CloudFront Console: https://console.aws.amazon.com/cloudfront/v3/home#/distributions/E1XWXVYFO71217

**OnlyDomains Support**:
- Website: https://www.onlydomains.com
- Help: https://www.onlydomains.com/support

---

**Migration Prepared By**: Claude Code
**Date**: November 1, 2025
**Document Version**: 1.0
**Status**: ✅ Ready for nameserver update at OnlyDomains.com
