# AWS Cost-Optimization Quick Reference
# Yoto Smart Stream - Decision Matrix

**Purpose:** Fast reference for AWS architecture decisions  
**Full Report:** See [AWS_COST_OPTIMIZATION_REPORT.md](AWS_COST_OPTIMIZATION_REPORT.md)

---

## TL;DR Recommendations

| Scenario | Recommended Architecture | Monthly Cost | Key Trade-off |
|----------|-------------------------|--------------|---------------|
| **Personal/Home Use** | Lambda + Fargate Spot | $5-8 | Cold starts OK |
| **Small Business** | Hybrid (Lambda + Fargate) | $8-12 | Balance cost/performance |
| **Production/Growth** | ALB + Fargate + DynamoDB | $33 | No cold starts |
| **Ultra-Minimal** | Lambda only (no MQTT) | $2-3 | No real-time events |

---

## Architecture Comparison Matrix

|  | **Arch 1: Minimal** | **Arch 2: No Cold Starts** | **Arch 3: Hybrid** | **Railway (Current)** |
|--|-------------------|------------------------|------------------|-------------------|
| **Monthly Cost** | **$5-8** | $33-47 | **$8-12** | $5 (Hobby) / $20 (Pro) |
| **API Cold Starts** | Yes (2-5s) | No | Yes (infrequent) | No |
| **MQTT Always-On** | Yes (Spot) | Yes | Yes (Spot) | Yes |
| **Scalability** | Unlimited | Unlimited | Unlimited | Limited (Hobby) |
| **Complexity** | Medium | Low | Medium | Very Low |
| **Best For** | Low traffic, cost-sensitive | Production, performance-critical | Small business, growth | Simple deployment |

---

## Component Cost Breakdown (Architecture 1 - Minimal)

| Component | Service | Monthly Cost | Notes |
|-----------|---------|--------------|-------|
| API Endpoints | Lambda + API Gateway | $0.50-1 | Free tier covers most usage |
| MQTT Handler | ECS Fargate Spot (0.25 vCPU) | $2-3 | 70% discount vs on-demand |
| Database | DynamoDB On-Demand | $0.50-1 | 25GB free tier |
| Audio Storage | S3 Standard | $0.50-1 | ~2GB storage + bandwidth |
| Static UI | S3 + CloudFront | $0.50 | 1TB free tier (12 months) |
| Background Jobs | Lambda + EventBridge | $0 | Free tier |
| Monitoring | CloudWatch | $0.50 | Logs + metrics |
| **TOTAL** | | **$5-8** | With free tier benefits |

---

## Component Decision Guide

### API Endpoints

| Option | Cost | Pros | Cons | Use When |
|--------|------|------|------|----------|
| **Lambda + API Gateway** | $0.50-1 | Scales to zero, cheap | Cold starts | Traffic is bursty |
| **ECS Fargate** | $15+ | No cold starts | Always-on cost | Need instant response |
| **EC2 t4g.nano Spot** | $1-2 | Very cheap | Manual management | Comfortable with EC2 |

**Recommendation:** Lambda for home use, Fargate for production

---

### MQTT Handler (Long-Running)

| Option | Cost | Pros | Cons | Use When |
|--------|------|------|------|----------|
| **ECS Fargate Spot** | $2-3 | 70% savings, auto-recovery | Rare interruptions | Cost priority |
| **ECS Fargate On-Demand** | $7-10 | No interruptions | More expensive | Need 100% uptime |
| **EC2 t4g.nano Spot** | $1-2 | Cheapest | Manual management | Comfortable with EC2 |

**Recommendation:** Fargate Spot (best cost/simplicity balance)

---

### Database

| Option | Cost | Pros | Cons | Use When |
|--------|------|------|------|----------|
| **DynamoDB On-Demand** | $0.50-1 | Serverless, cheap at low volume | NoSQL, schema change | <10K requests/day |
| **RDS db.t4g.micro** | $13-15 | SQL, easy migration | Always-on cost | Need SQL compatibility |
| **Aurora Serverless v2** | $36+ | Scales, SQL | Expensive | High traffic only |

**Recommendation:** DynamoDB for cost, RDS if SQL is critical

---

### Audio Storage

| Option | Cost | Pros | Cons | Use When |
|--------|------|------|------|----------|
| **S3 Standard** | $0.50-1 | Fast access, CDN-ready | | Default choice |
| **S3 Intelligent-Tiering** | $0.30-1 | Auto-optimizes cost | Slight overhead | Mix of hot/cold files |
| **S3 Glacier** | $0.10-0.30 | Very cheap | Slow retrieval | Archive only |

**Recommendation:** S3 Standard + CloudFront CDN

---

## Free Tier Value

### Permanent Free Tier (Always Available)
- **Lambda:** 1M requests + 400K GB-seconds/month = ~$20 value
- **DynamoDB:** 25GB storage + 200M requests/month = ~$10 value
- **CloudWatch:** 10 custom metrics + 5GB logs = ~$2 value
- **S3:** (First 5GB free for 12 months only)

**Total Permanent Value:** ~$32/month in free compute/storage

### First 12 Months Free Tier
- **API Gateway:** 1M requests/month = ~$1 value
- **CloudFront:** 1TB transfer + 10M requests/month = ~$10 value
- **S3:** 5GB storage + 20K GET requests/month = ~$0.15 value

**Total First Year Bonus:** +$11/month for 12 months

---

## Cost-Saving Tips

### Quick Wins (No Code Changes)
1. **Enable S3 Lifecycle Policies:** Move old audio to Glacier after 90 days (-$0.50/month)
2. **Use CloudFront Caching:** Cache audio for 24 hours (-$0.30/month)
3. **Compress Audio:** 128kbps MP3 instead of 256kbps (-$0.50/month storage + bandwidth)
4. **Use Fargate Spot:** 70% discount for MQTT (-$5/month)
5. **DynamoDB On-Demand:** vs. Provisioned Capacity (-$10-20/month at low traffic)

**Total Quick Savings:** $7-10/month with minimal effort

### Medium Effort
6. **Lambda Layers:** Share dependencies across functions (-$0.10/month storage)
7. **S3 Intelligent-Tiering:** Auto-optimize based on access patterns (-$0.20/month)
8. **Reserved Capacity (DynamoDB):** If traffic is predictable (-10-20% cost)

### Advanced
9. **Lambda Savings Plan:** 1-year commit for 17% discount (if >$50/month Lambda)
10. **Compute Savings Plan:** For Fargate (if >$100/month compute)

---

## Migration Effort Estimate

| Phase | Task | Time | Complexity |
|-------|------|------|------------|
| 1 | Move audio to S3, test streaming | 8 hours | Low |
| 2 | Migrate database to DynamoDB | 16 hours | Medium |
| 3 | Deploy MQTT to Fargate | 8 hours | Medium |
| 4 | Deploy API to Lambda | 12 hours | Medium |
| 5 | Setup UI on S3/CloudFront | 4 hours | Low |
| 6 | Testing and debugging | 12 hours | Medium |
| **Total** | | **60 hours** | **2-4 weeks** |

**Skills Required:**
- AWS basics (IAM, S3, Lambda)
- Docker (for Fargate)
- Python (code adaptations)
- IaC (SAM or Terraform)

---

## Decision Tree

```
Start: Do you need MQTT real-time events?
├─ No  → Lambda only ($2-3/month, API only)
└─ Yes → Are cold starts acceptable?
    ├─ Yes (home use) → Architecture 1 (Lambda + Fargate Spot, $5-8/month) ✓
    └─ No (production) → Is SQL database required?
        ├─ No  → Architecture 3 (Hybrid + DynamoDB, $8-12/month) ✓
        └─ Yes → Architecture 2 (Fargate + RDS, $47/month)

Is Railway Hobby sufficient for your usage?
├─ Yes → Stay on Railway ($5/month, simplest)
└─ No  → Migrate to AWS for unlimited usage
```

---

## When to Stay on Railway

**Stay on Railway if:**
- ✅ Monthly usage < 500 hours (Hobby plan)
- ✅ Simplicity is more important than cost optimization
- ✅ Don't want to manage AWS complexity
- ✅ No need for multi-region or advanced AWS features

**Migrate to AWS if:**
- ✅ Need unlimited compute (exceeding 500 hours/month)
- ✅ Want to optimize costs at higher usage
- ✅ Need specific AWS services (e.g., Polly, Rekognition)
- ✅ Comfortable with AWS and IaC

---

## Cost at Different Usage Levels

| Usage Level | Requests/Day | Audio Streams/Day | Arch 1 (Minimal) | Arch 3 (Hybrid) | Railway Pro |
|-------------|--------------|-------------------|------------------|-----------------|-------------|
| **Low (Home)** | 100-500 | 5-20 | **$5-8** | $8-12 | $20 |
| **Medium (Small Biz)** | 1K-5K | 50-200 | **$8-12** | $12-18 | $20+ |
| **High (Scale)** | 10K-50K | 500-2K | **$15-25** | $25-40 | $50+ |
| **Very High** | 100K+ | 5K+ | **$40-60** | $60-100 | $100+ |

**Insight:** AWS becomes more cost-effective as usage increases, Railway is simpler for very low traffic.

---

## Next Steps

1. **Review full report:** [AWS_COST_OPTIMIZATION_REPORT.md](AWS_COST_OPTIMIZATION_REPORT.md)
2. **Choose architecture:** Based on usage and priorities
3. **Setup AWS account:** Create account, configure billing alerts
4. **Start migration:** Begin with Phase 1 (S3 storage)
5. **Validate and iterate:** Test each component before moving to next

---

## Quick Links

- **Full Architecture Report:** [AWS_COST_OPTIMIZATION_REPORT.md](AWS_COST_OPTIMIZATION_REPORT.md)
- **AWS Calculator:** https://calculator.aws/
- **AWS Free Tier:** https://aws.amazon.com/free/
- **AWS SAM Documentation:** https://docs.aws.amazon.com/serverless-application-model/

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-15  
**See Full Report:** AWS_COST_OPTIMIZATION_REPORT.md
