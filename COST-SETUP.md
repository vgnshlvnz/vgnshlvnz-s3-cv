# AWS Cost Monitoring Setup Guide

## Overview
This guide helps you set up comprehensive cost monitoring and alerts to ensure your Job Tracker and Portfolio infrastructure stays within the AWS free tier and doesn't incur unexpected charges.

**Target Budget**: MYR 0-10/month (~$0-2 USD/month)

---

## Phase 1: AWS Budgets Setup

### Step 1: Create Monthly Cost Budget

1. Navigate to [AWS Budgets Console](https://console.aws.amazon.com/billing/home#/budgets)
2. Click **Create budget**
3. Select **Cost budget** → **Next**

#### Budget Configuration

```
Budget name:           JobTracker-Monthly-Budget
Period:                Monthly
Budget effective dates: Recurring budget
Start month:           Current month
Budgeting method:      Fixed
Budgeted amount:       $5.00 USD (or MYR 25)
```

#### Budget Scope (Optional Filters)

Add tags to track specific projects:
```
Tag key:   Project
Tag value: JobTracker
```

Or filter by service:
```
Services: S3, Lambda, API Gateway, DynamoDB (if enabled)
```

#### Alert Thresholds

Create **3 alerts** at different thresholds:

**Alert 1: 50% Threshold (Early Warning)**
```
Threshold:         50% of budgeted amount
Trigger:           Actual costs
Email recipients:  your-email@example.com
```

**Alert 2: 80% Threshold (Warning)**
```
Threshold:         80% of budgeted amount
Trigger:           Actual costs
Email recipients:  your-email@example.com
```

**Alert 3: 100% Threshold (Critical)**
```
Threshold:         100% of budgeted amount
Trigger:           Actual costs
Email recipients:  your-email@example.com
SNS topic:         (Optional) Create SNS topic for additional notifications
```

4. Click **Create budget**

---

### Step 2: Create Free Tier Usage Budget

Track free tier usage to avoid unexpected charges:

1. In AWS Budgets, click **Create budget**
2. Select **Usage budget** → **Next**

#### Configuration

```
Budget name:     Free-Tier-Tracker
Usage type:      Usage Type Group
Usage group:     S3: All data transfer usage
Period:          Monthly
Budgeted amount: 20000 (requests for S3 GET)
```

#### Create Multiple Usage Budgets for:

**S3 Storage**
```
Budget name:     S3-Storage-Usage
Usage type:      GB-Month
Budgeted amount: 5 (5GB free tier)
```

**Lambda Invocations**
```
Budget name:     Lambda-Invocations
Usage type:      Invocations
Budgeted amount: 1000000 (1M requests free tier)
```

**API Gateway Requests**
```
Budget name:     API-Gateway-Requests
Usage type:      Number of Requests
Budgeted amount: 1000000 (1M requests free tier)
```

---

## Phase 2: AWS Cost Anomaly Detection

### Setup Cost Anomaly Monitor

1. Navigate to [Cost Anomaly Detection](https://console.aws.amazon.com/cost-management/home#/anomaly-detection)
2. Click **Create monitor**

#### Monitor Configuration

```
Monitor name:         JobTracker-Anomaly-Monitor
Monitor type:         AWS Service
Service:              All AWS Services
Alerting preference:  Individual alerts
```

#### Alert Subscription

1. Create an **Alert subscription**
2. Configure:

```
Subscription name:    JobTracker-Alerts
Threshold:            $1.00 USD
Frequency:            Daily
Recipients:           your-email@example.com
```

This will alert you if costs spike unexpectedly by $1 or more.

---

## Phase 3: Free Tier Usage Alerts

### Enable Free Tier Alerts

1. Go to [Billing Preferences](https://console.aws.amazon.com/billing/home#/preferences)
2. Scroll to **Alert preferences**
3. Check **Receive Free Tier Usage Alerts**
4. Enter your email address
5. Click **Save preferences**

**You'll receive alerts when**:
- You exceed 85% of the free tier limit for any service
- You approach free tier expiration (for 12-month free tier)

---

## Phase 4: CloudWatch Logs Cost Optimization

### Set Log Retention Policies

Lambda functions generate logs that cost $0.50/GB ingested + $0.03/GB stored per month. Let's optimize:

#### Via AWS Console

1. Go to [CloudWatch Logs Console](https://console.aws.amazon.com/cloudwatch/home?region=ap-southeast-5#logsV2:log-groups)
2. Find `/aws/lambda/vgnshlvnz-job-tracker-api`
3. Click **Actions** → **Edit retention setting**
4. Set to: **7 days** (dev) or **14 days** (prod)
5. Click **Save**

#### Via AWS CLI

```bash
# Set 7-day retention for job tracker Lambda
aws logs put-retention-policy \
  --log-group-name /aws/lambda/vgnshlvnz-job-tracker-api \
  --retention-in-days 7 \
  --region ap-southeast-5

# Verify
aws logs describe-log-groups \
  --log-group-name-prefix /aws/lambda/vgnshlvnz-job-tracker \
  --query 'logGroups[*].[logGroupName,retentionInDays]' \
  --output table \
  --region ap-southeast-5
```

---

## Phase 5: S3 Cost Optimization

### Lifecycle Policies (Already in SAM Templates)

The job tracker S3 bucket already has lifecycle rules:

**applications/ prefix:**
- 30 days → Intelligent-Tiering
- 180 days → Glacier Instant Retrieval
- Old versions → Standard-IA @ 30 days → Glacier @ 90 days
- Delete old versions after 365 days

**uploads/tmp/ prefix:**
- Delete after 7 days
- Abort incomplete multipart uploads after 1 day

### Monitor S3 Storage

```bash
# Check current S3 storage usage
aws s3api list-buckets --query "Buckets[].Name" --output text | \
while read bucket; do
    echo "=== $bucket ==="
    aws cloudwatch get-metric-statistics \
      --namespace AWS/S3 \
      --metric-name BucketSizeBytes \
      --dimensions Name=BucketName,Value=$bucket Name=StorageType,Value=StandardStorage \
      --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
      --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
      --period 86400 \
      --statistics Average \
      --region ap-southeast-5 \
      --query 'Datapoints[0].Average' \
      --output text | awk '{printf "%.2f GB\n", $1/1024/1024/1024}'
done
```

---

## Phase 6: Resource Tagging for Cost Allocation

### Enable Cost Allocation Tags

1. Go to [Cost Allocation Tags](https://console.aws.amazon.com/billing/home#/tags)
2. Activate these tags:

```
- Project
- Environment
- ManagedBy
- CostCenter
```

3. Wait 24 hours for tags to appear in Cost Explorer

### Verify Tags on Resources

```bash
# Check job tracker bucket tags
aws s3api get-bucket-tagging \
  --bucket vgnshlvnz-job-tracker \
  --region ap-southeast-5

# Check Lambda function tags
aws lambda list-tags \
  --resource arn:aws:lambda:ap-southeast-5:ACCOUNT_ID:function:vgnshlvnz-job-tracker-api

# Check API Gateway tags
aws apigatewayv2 get-tags \
  --resource-arn arn:aws:apigateway:ap-southeast-5::/apis/API_ID
```

---

## Phase 7: Cost Explorer Setup

### Enable Cost Explorer

1. Go to [Cost Explorer](https://console.aws.amazon.com/cost-management/home#/cost-explorer)
2. Click **Enable Cost Explorer** (if not already enabled)
3. Wait 24 hours for data to populate

### Create Custom Cost Reports

#### Report 1: Daily Costs by Service

```
Report name:    Daily Service Costs
Time period:    Last 7 days
Granularity:    Daily
Group by:       Service
Filters:        None
```

#### Report 2: Monthly Costs by Tag

```
Report name:    Project Costs
Time period:    Month to date
Granularity:    Monthly
Group by:       Tag: Project
Filters:        Tag: Project = JobTracker
```

#### Report 3: Free Tier Usage

```
Report name:    Free Tier Tracker
Time period:    Month to date
Granularity:    Monthly
Filters:        Usage type: Free Tier
```

### Save Reports

Click **Save report** for each to access quickly from the dashboard.

---

## Phase 8: Lambda Cost Optimization

### Right-Size Lambda Memory

Monitor Lambda performance and adjust memory:

```bash
# Get Lambda cost metrics
aws lambda get-function \
  --function-name vgnshlvnz-job-tracker-api \
  --query 'Configuration.{Memory:MemorySize,Timeout:Timeout,Runtime:Runtime}' \
  --output table
```

**Current settings:**
- Memory: 256 MB
- Architecture: arm64 (Graviton2 - 20% cheaper)

**Cost calculation:**
- 256 MB = $0.0000033 per 100ms (arm64)
- 1M requests @ 200ms each = $0.66/month
- Within free tier: 400,000 GB-seconds/month

### Monitor with CloudWatch Insights

```bash
# Get average execution time
aws logs tail /aws/lambda/vgnshlvnz-job-tracker-api --since 7d --format short | \
  grep "REPORT" | \
  awk '{print $5}' | \
  awk '{sum+=$1; count++} END {print "Avg duration:", sum/count, "ms"}'
```

If average < 100ms: Consider reducing to 128 MB
If average > 500ms: Consider increasing to 512 MB

---

## Phase 9: SNS Topic for Consolidated Alerts (Optional)

### Create SNS Topic

```bash
# Create SNS topic
aws sns create-topic \
  --name JobTracker-Cost-Alerts \
  --region ap-southeast-5

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:ap-southeast-5:ACCOUNT_ID:JobTracker-Cost-Alerts \
  --protocol email \
  --notification-endpoint your-email@example.com

# Confirm subscription via email
```

### Update Budget to Use SNS

1. Edit your budget
2. Add SNS topic ARN to 100% threshold alert
3. This allows programmatic responses to budget alerts

---

## Phase 10: Monthly Cost Review Checklist

### Review Every Month

- [ ] Check AWS Budgets dashboard
- [ ] Review Cost Explorer reports
- [ ] Check for cost anomalies
- [ ] Review S3 storage usage
- [ ] Check Lambda invocation count
- [ ] Review API Gateway request count
- [ ] Verify CloudWatch Logs retention
- [ ] Check for unused resources
- [ ] Review DynamoDB usage (if enabled)
- [ ] Verify no unexpected charges

### Cost Optimization Commands

```bash
# 1. List all S3 buckets and sizes
aws s3 ls | awk '{print $3}' | while read bucket; do
    size=$(aws s3 ls s3://$bucket --recursive --summarize 2>/dev/null | grep "Total Size" | awk '{print $3}')
    echo "$bucket: $((size / 1024 / 1024)) MB"
done

# 2. Count objects in job tracker bucket
aws s3api list-objects-v2 \
  --bucket vgnshlvnz-job-tracker \
  --prefix applications/ \
  --query 'length(Contents)'

# 3. Get Lambda invocations last 7 days
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=vgnshlvnz-job-tracker-api \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 604800 \
  --statistics Sum \
  --region ap-southeast-5

# 4. Get API Gateway requests
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=vgnshlvnz-job-tracker-api \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 604800 \
  --statistics Sum \
  --region ap-southeast-5
```

---

## Expected Monthly Costs

### Within Free Tier (First 12 Months)

| Service | Free Tier | Expected Usage | Cost |
|---------|-----------|----------------|------|
| S3 Storage | 5 GB | 0.1-0.5 GB | $0.00 |
| S3 Requests (GET) | 20,000 | 1,000-5,000 | $0.00 |
| S3 Requests (PUT) | 2,000 | 50-200 | $0.00 |
| Lambda Requests | 1M | 10,000-50,000 | $0.00 |
| Lambda Compute | 400,000 GB-sec | 20,000 GB-sec | $0.00 |
| API Gateway | 1M calls | 10,000-50,000 | $0.00 |
| CloudWatch Logs | 5 GB | 0.05 GB | $0.00 |
| **Total** | | | **$0.00** |

### After Free Tier (Month 13+)

| Service | Expected Usage | Cost |
|---------|----------------|------|
| S3 Storage | 1 GB | $0.023 |
| S3 Requests | 5,000 GET, 100 PUT | $0.002 |
| Lambda | 20,000 requests @ 200ms | $0.02 |
| API Gateway | 20,000 requests | $0.02 |
| CloudWatch Logs | 0.1 GB | $0.05 |
| **Total** | | **~$0.11 USD** |

**In MYR**: ~MYR 0.50/month

---

## Alerts You Should Receive

### Normal Operations (No Alerts)

When everything is working correctly, you should receive:
- Monthly free tier usage report (if enabled)
- End-of-month budget summary

### Warning Alerts

- **50% Budget Alert**: Review spending, check for unexpected usage
- **80% Budget Alert**: Investigate immediately, identify cost drivers
- **85% Free Tier Alert**: Monitor closely, may need to optimize

### Critical Alerts

- **100% Budget Alert**: STOP creating resources, review all services
- **Cost Anomaly Alert**: Unexpected spike detected, investigate cause
- **Free Tier Exceeded**: Charges will begin, optimize or increase budget

---

## Troubleshooting High Costs

### If You Receive a High Cost Alert

1. **Check Cost Explorer** → Identify which service is expensive
2. **Review Recent Changes** → Did you deploy new resources?
3. **Check S3 bucket sizes** → Run size check command above
4. **Review Lambda invocations** → Are there infinite loops?
5. **Check API Gateway** → Is someone spamming your API?
6. **Look for orphaned resources** → Unused EC2, EBS, snapshots

### Common Cost Culprits

| Issue | Solution |
|-------|----------|
| Infinite Lambda loop | Add timeout, check logs, fix code |
| API Gateway abuse | Add throttling, API key requirement |
| Large S3 uploads | Add size limits, lifecycle policies |
| Forgotten resources | Regular cleanup, use tags |
| Old CloudWatch Logs | Set retention to 7-14 days |
| Old S3 versions | Enable lifecycle to delete old versions |

---

## Cost Optimization Tips

1. **Use Graviton2 (arm64)** for Lambda - 20% cheaper than x86 ✅ (Already configured)
2. **HTTP API vs REST API** - HTTP API is cheaper ✅ (Already using HTTP API)
3. **Intelligent-Tiering** for S3 - Automatic cost savings ✅ (Already configured)
4. **Short log retention** - 7-14 days max ✅ (Already configured)
5. **Presigned URLs** - No Lambda invocation for file uploads ✅ (Already using)
6. **S3 lifecycle** - Auto-delete tmp files ✅ (Already configured)
7. **On-demand DynamoDB** - Pay per request (if you enable DynamoDB later)

---

## Summary Checklist

After completing this guide, you should have:

- [ ] Monthly cost budget with 3 alert thresholds
- [ ] Free tier usage tracking budgets
- [ ] Cost anomaly detection enabled
- [ ] Free tier alerts enabled
- [ ] CloudWatch Logs retention set to 7-14 days
- [ ] S3 lifecycle policies active
- [ ] Cost allocation tags activated
- [ ] Cost Explorer enabled with saved reports
- [ ] SNS topic for consolidated alerts (optional)
- [ ] Monthly review process established

**Expected total cost: $0-2 USD/month (~MYR 0-10/month)**

---

**Document Version**: 1.0
**Last Updated**: November 1, 2025
**Next Review**: December 1, 2025
