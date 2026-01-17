# AWS Architecture Visual Comparison
# Yoto Smart Stream

This document provides visual ASCII diagrams of the three recommended AWS architectures for easy comparison.

---

## Architecture 1: Minimal Cost ($5-8/month)
**Best for:** Personal/home use, low traffic, cost-sensitive

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Internet / Yoto Devices                        │
│                    (Users, Yoto Players, Yoto API)                    │
└─────────────┬────────────────────────────────────────────────────────┘
              │
              │ HTTPS Requests
              │
┌─────────────▼──────────────────────────────────────────────────┐
│              AWS API Gateway (HTTP API)                         │
│  • REST endpoints: /api/players, /api/cards, /api/library      │
│  • Serverless, pay-per-request                                 │
│  • Cost: ~$0.50/month (within free tier)                       │
└─────────────┬──────────────────────────────────────────────────┘
              │
              │ Triggers Lambda
              │
┌─────────────▼──────────────────────────────────────────────────┐
│              AWS Lambda (Python FastAPI)                        │
│  • Handler: Mangum adapter for FastAPI                         │
│  • Runtime: Python 3.9, 1GB RAM, 30s timeout                   │
│  • Routes: Players, Cards, Library, Admin, Auth               │
│  • SCALES TO ZERO when not in use                              │
│  • Cold start: 2-5 seconds (first request after idle)          │
│  • Cost: FREE (within 1M requests/month free tier)             │
└─────┬───────────────────────────────────────────┬───────────────┘
      │                                           │
      │ Reads/Writes                              │ Reads/Writes
      │                                           │
┌─────▼─────────────────────────┐    ┌───────────▼──────────────────┐
│   DynamoDB (On-Demand)        │    │   S3 Bucket (Audio + UI)     │
│  • Single table design        │    │  • audio/ - MP3 files        │
│  • Users + OAuth tokens       │    │  • static/ - HTML/CSS/JS     │
│  • Event log (optional)       │    │  • icons/ - Cover images     │
│  • Serverless, pay per req    │    │  • Pre-signed URLs (1 hour)  │
│  • Cost: ~$0.50-1/month       │    │  • Cost: ~$0.50-1/month      │
└───────────────────────────────┘    └──────────┬───────────────────┘
                                                 │
                                     ┌───────────▼──────────────────┐
                                     │   CloudFront CDN (Optional)  │
                                     │  • Cache static UI globally  │
                                     │  • Cache popular audio files │
                                     │  • Cost: ~$0.50/month        │
                                     │  • 1TB free tier (12 months) │
                                     └──────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│           ECS Fargate Spot (MQTT Handler)                             │
│  • Container: Python MQTT client (separate from API)                 │
│  • Size: 0.25 vCPU, 0.5GB RAM                                        │
│  • ALWAYS RUNNING (persistent MQTT connection to mqtt.yoto.io)       │
│  • Auto-reconnects on Spot interruption (rare)                       │
│  • Includes: Token refresh task (every 12 hours)                     │
│  • Cost: ~$2-3/month (70% discount with Spot pricing)                │
└─────────────┬────────────────────────────────────────────────────────┘
              │
              │ Writes events to DynamoDB
              │
              └──────────────► [DynamoDB]


TOTAL MONTHLY COST: $5-8

Breakdown:
  - API Gateway:        $0.50  (within free tier)
  - Lambda:             $0     (within free tier)
  - DynamoDB:           $1     (25GB free + pay per request)
  - S3 + CloudFront:    $1     (storage + bandwidth)
  - Fargate Spot MQTT:  $3     (0.25 vCPU, 70% discount)
  - CloudWatch Logs:    $0.50  (monitoring)
  ─────────────────────────
  TOTAL:                $6

Pros:
  ✓ Lowest cost option
  ✓ API scales to zero when not in use
  ✓ Unlimited scalability (Lambda auto-scales)
  ✓ MQTT always-on for real-time events
  ✓ 70% savings on MQTT with Spot pricing

Cons:
  ✗ Cold starts (2-5s) on first API call after idle
  ✗ Rare Spot interruptions (auto-recovers)
  ✗ More complex deployment than single container
```

---

## Architecture 2: No Cold Starts ($33-47/month)
**Best for:** Production apps, performance-critical, no cold start tolerance

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Internet / Yoto Devices                        │
│                    (Users, Yoto Players, Yoto API)                    │
└─────────────┬────────────────────────────────────────────────────────┘
              │
              │ HTTPS Requests
              │
┌─────────────▼──────────────────────────────────────────────────┐
│        Application Load Balancer (ALB)                          │
│  • Public endpoint with SSL/TLS termination                     │
│  • Health checks on /api/health                                 │
│  • Routes to Fargate target group                               │
│  • ALWAYS RUNNING (fixed cost)                                  │
│  • Cost: ~$16/month base cost                                   │
└─────────────┬──────────────────────────────────────────────────┘
              │
              │ Forwards to Fargate
              │
┌─────────────▼──────────────────────────────────────────────────┐
│           ECS Fargate (Single Container)                        │
│  • Container: FastAPI + MQTT handler (combined)                │
│  • Size: 0.5 vCPU, 1GB RAM                                      │
│  • ALWAYS RUNNING (no cold starts)                              │
│  • FastAPI serves API + static files                            │
│  • Background tasks: MQTT + token refresh                       │
│  • Instant response time (<100ms)                               │
│  • Cost: ~$15/month (0.5 vCPU on-demand)                        │
└─────┬───────────────────────────────────────────┬───────────────┘
      │                                           │
      │ Reads/Writes                              │ Reads/Writes
      │                                           │
┌─────▼─────────────────────────┐    ┌───────────▼──────────────────┐
│   Option A: DynamoDB          │    │   S3 Bucket (Audio + UI)     │
│  • On-demand billing          │    │  • audio/ - MP3 files        │
│  • Cost: ~$1/month            │    │  • static/ - Served by ALB   │
└───────────────────────────────┘    │     (or from S3)             │
                                     │  • Cost: ~$1.50/month        │
┌─────────────────────────────┐     └──────────────────────────────┘
│   Option B: RDS db.t4g.micro │
│  • PostgreSQL or MySQL       │
│  • SQL compatibility (easy   │
│    migration from SQLite)    │
│  • 20GB storage              │
│  • ALWAYS RUNNING            │
│  • Cost: ~$15/month          │
└──────────────────────────────┘


TOTAL MONTHLY COST (Option A - DynamoDB): $33/month
TOTAL MONTHLY COST (Option B - RDS):      $47/month

Breakdown (with DynamoDB):
  - Application Load Balancer:  $16
  - ECS Fargate (0.5 vCPU):     $15
  - DynamoDB:                   $1
  - S3 Storage:                 $1
  - CloudWatch:                 $0.50
  ─────────────────────────────────
  TOTAL:                        $33.50

Breakdown (with RDS):
  - Application Load Balancer:  $16
  - ECS Fargate (0.5 vCPU):     $15
  - RDS db.t4g.micro:           $15
  - S3 Storage:                 $1
  - CloudWatch:                 $0.50
  ─────────────────────────────────
  TOTAL:                        $47.50

Pros:
  ✓ NO COLD STARTS (instant API response)
  ✓ Simple deployment (single container, like Railway)
  ✓ SQL database option (easy migration)
  ✓ Production-grade performance
  ✓ Easy to migrate from Railway (similar architecture)

Cons:
  ✗ ALWAYS-ON COST even when idle
  ✗ More expensive than Lambda at low usage
  ✗ Fixed resources (need to scale up for more traffic)
```

---

## Architecture 3: Hybrid (Recommended) ($8-12/month)
**Best for:** Small business, growth, balance of cost and performance

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Internet / Yoto Devices                        │
│                    (Users, Yoto Players, Yoto API)                    │
└─────────────┬────────────────────────────────────────────────────────┘
              │
              │ HTTPS Requests
              │
┌─────────────▼──────────────────────────────────────────────────┐
│              AWS API Gateway (HTTP API)                         │
│  • Routes to appropriate Lambda function                        │
│  • Cost: ~$0.50/month                                           │
└───┬─────────────────────────────────────────────────────────────┘
    │
    ├───────────────┬───────────────┬───────────────┬─────────────┐
    │               │               │               │             │
    │ /players      │ /cards        │ /library      │ /streams    │
    │               │               │               │             │
┌───▼─────────┐ ┌──▼──────────┐ ┌──▼──────────┐ ┌──▼──────────┐
│  Lambda     │ │  Lambda     │ │  Lambda     │ │  Lambda     │
│  Players    │ │  Cards      │ │  Library    │ │  Streams    │
│             │ │             │ │             │ │             │
│  Read-only  │ │  TTS gen    │ │  Browse     │ │  Playlist   │
│  operations │ │  Card CRUD  │ │  catalog    │ │  control    │
│             │ │             │ │             │ │             │
│  Cold start │ │  Cold start │ │  Cold start │ │  Cold start │
│  acceptable │ │  acceptable │ │  acceptable │ │  acceptable │
└─────┬───────┘ └──┬──────────┘ └──┬──────────┘ └──┬──────────┘
      │            │               │               │
      │ Cost: Included in Lambda free tier (1M req/month)
      │
      └────────────┴───────────────┴───────────────┴─────────────┐
                                                                  │
      ┌───────────────────────────────────────────────────────────┘
      │
      │ All Lambdas read/write to:
      │
┌─────▼─────────────────────────┐    ┌────────────────────────────┐
│   DynamoDB (On-Demand)        │    │   S3 + CloudFront          │
│  • Single table design        │    │  • audio/ - MP3 files      │
│  • Users + tokens             │    │  • static/ - UI files      │
│  • Cost: ~$1/month            │    │  • Cost: ~$1.50/month      │
└───────────────────────────────┘    └────────────────────────────┘


┌──────────────────────────────────────────────────────────────────────┐
│           ECS Fargate Spot (MQTT Handler)                             │
│  • Separate container just for MQTT                                  │
│  • Size: 0.25 vCPU, 0.5GB RAM                                        │
│  • ALWAYS RUNNING (persistent connection)                            │
│  • Spot pricing: 70% discount                                        │
│  • Also runs: Background token refresh (every 12 hours)              │
│  • Writes events to DynamoDB                                         │
│  • Cost: ~$3/month                                                   │
└───────────────────────────────────────────────────────────────────────┘


TOTAL MONTHLY COST: $8-12

Breakdown:
  - API Gateway:        $0.50
  - Lambda (all):       $1     (mostly within free tier)
  - DynamoDB:           $1
  - S3 + CloudFront:    $1.50
  - Fargate Spot MQTT:  $3
  - CloudWatch:         $0.50
  - EventBridge:        $0     (token refresh scheduler)
  ─────────────────────────
  TOTAL:                $7.50 (low usage) to $12 (medium usage)

Pros:
  ✓ BALANCED cost and performance
  ✓ API scales to zero (most endpoints on Lambda)
  ✓ MQTT always-on for real-time events
  ✓ Cold starts only on infrequent API calls
  ✓ 70% savings on MQTT with Spot
  ✓ Can scale Lambda independently for hot endpoints

Cons:
  ✗ Cold starts on first request to each endpoint
  ✗ Slightly more complex than Architecture 2
  ✗ Rare Spot interruptions on MQTT (auto-recovers)

Best Use Cases:
  • Small business with growing user base
  • Home use that occasionally exceeds Hobby tier
  • Apps where some cold starts are acceptable
  • Need balance between cost optimization and performance
```

---

## Side-by-Side Comparison

```
┌───────────────────┬────────────────┬────────────────┬────────────────┐
│      Aspect       │   Arch 1       │   Arch 2       │   Arch 3       │
│                   │   (Minimal)    │ (No Cold Start)│   (Hybrid)     │
├───────────────────┼────────────────┼────────────────┼────────────────┤
│ Monthly Cost      │   $5-8         │   $33-47       │   $8-12        │
├───────────────────┼────────────────┼────────────────┼────────────────┤
│ API Cold Starts   │   Yes (2-5s)   │   NO           │   Some         │
├───────────────────┼────────────────┼────────────────┼────────────────┤
│ MQTT Always-On    │   Yes (Spot)   │   Yes          │   Yes (Spot)   │
├───────────────────┼────────────────┼────────────────┼────────────────┤
│ API Scalability   │   Unlimited    │   Manual       │   Unlimited    │
├───────────────────┼────────────────┼────────────────┼────────────────┤
│ Deployment        │   Medium       │   Easy         │   Medium       │
│ Complexity        │                │                │                │
├───────────────────┼────────────────┼────────────────┼────────────────┤
│ Database          │   DynamoDB     │   DynamoDB/RDS │   DynamoDB     │
├───────────────────┼────────────────┼────────────────┼────────────────┤
│ Idle Cost         │   $3/month     │   $33-47/month │   $3/month     │
│ (when not used)   │   (MQTT only)  │   (full stack) │   (MQTT only)  │
├───────────────────┼────────────────┼────────────────┼────────────────┤
│ Best For          │   Personal/    │   Production/  │   Small        │
│                   │   Home use     │   Enterprise   │   Business     │
└───────────────────┴────────────────┴────────────────┴────────────────┘
```

---

## Key Decision Factors

### Choose Architecture 1 (Minimal) if:
- ✅ Cost is top priority
- ✅ Traffic is bursty/unpredictable
- ✅ 2-5 second cold start is acceptable
- ✅ Personal/home use
- ✅ Want to minimize idle costs

### Choose Architecture 2 (No Cold Starts) if:
- ✅ Performance is critical
- ✅ Cannot tolerate cold starts
- ✅ Need instant API response (<100ms)
- ✅ Want simple deployment (like Railway)
- ✅ Budget allows $35-50/month

### Choose Architecture 3 (Hybrid) if:
- ✅ Want balance of cost and performance
- ✅ Some APIs can tolerate cold starts
- ✅ Growing user base
- ✅ Need MQTT always-on
- ✅ Budget is $10-15/month

---

## Traffic Pattern Impact

```
Low Traffic (100-500 requests/day):
  Arch 1: $5-6/month  ◄── BEST
  Arch 2: $33/month
  Arch 3: $8-9/month

Medium Traffic (1K-5K requests/day):
  Arch 1: $8-10/month ◄── GOOD
  Arch 2: $33/month
  Arch 3: $10-12/month ◄── BEST (balanced)

High Traffic (10K+ requests/day):
  Arch 1: $15-20/month ◄── STILL CHEAPER
  Arch 2: $35-40/month
  Arch 3: $18-25/month

Very High Traffic (100K+ requests/day):
  Arch 1: $40-60/month
  Arch 2: $50-100/month (may need to scale Fargate)
  Arch 3: $60-80/month

Note: At very high traffic, all architectures become comparable in cost.
Lambda's pay-per-request model catches up to always-on Fargate costs.
```

---

## Free Tier Benefits (First 12 Months)

All architectures benefit from AWS Free Tier:

```
Permanent Free Tier (Always):
  - Lambda: 1M requests/month = $20 value
  - DynamoDB: 25GB + 200M requests/month = $10 value
  - CloudWatch: 10 metrics + 5GB logs = $2 value
  ───────────────────────────────────────────
  Total permanent value: $32/month

First 12 Months Only:
  - API Gateway: 1M requests/month = $1 value
  - CloudFront: 1TB transfer = $10 value
  - S3: 5GB storage + 20K GET = $0.15 value
  ───────────────────────────────────────────
  Additional first year value: $11/month

TOTAL FREE TIER VALUE: $43/month (first year), $32/month (after)

This means Architecture 1 can run nearly FREE for 12 months if traffic
is low, and Architecture 3 costs only $5-8/month after free tier value.
```

---

## Component Costs at a Glance

```
Component              Cost (Low)   Cost (Medium)   Notes
─────────────────────────────────────────────────────────────
Lambda (API)           $0-0.50      $1-2           Within free tier
API Gateway            $0.50        $1-2           Per million requests
DynamoDB               $0.50        $1-3           On-demand billing
S3 Storage (2GB)       $0.05        $0.10          Storage only
S3 GET requests        $0.20        $0.50          Per 1K requests
CloudFront             $0.50        $1-2           CDN + caching
Fargate Spot (0.25)    $2-3         $2-3           Fixed (MQTT)
Fargate (0.5 vCPU)     $15          $15            Fixed (always-on)
ALB                    $16          $16            Fixed
RDS db.t4g.micro       $15          $15            Fixed
CloudWatch             $0.50        $1             Logs + metrics
EventBridge            $0           $0             Free tier
```

---

## Migration Complexity Visual

```
Current (Railway) ──────┐
                        │
                        ▼
         ┌──────────────────────────┐
         │  Phase 1: Move Audio     │
         │  to S3 (1 week)          │ ◄── Easiest
         └────────────┬─────────────┘
                      │
                      ▼
         ┌──────────────────────────┐
         │  Phase 2: Migrate DB     │
         │  to DynamoDB (2 weeks)   │ ◄── Most effort
         └────────────┬─────────────┘
                      │
                      ▼
         ┌──────────────────────────┐
         │  Phase 3: Deploy MQTT    │
         │  to Fargate (1 week)     │
         └────────────┬─────────────┘
                      │
                      ▼
         ┌──────────────────────────┐
         │  Phase 4: Deploy API     │
         │  to Lambda (2 weeks)     │ ◄── Arch 1 & 3 only
         └────────────┬─────────────┘
                      │
                      ▼
         ┌──────────────────────────┐
         │  Phase 5: Static UI      │
         │  to S3/CloudFront        │
         └────────────┬─────────────┘
                      │
                      ▼
         ┌──────────────────────────┐
         │  Phase 6: Test & Cutover │
         │  (1 week)                │
         └──────────────────────────┘

Total Time: 6-8 weeks
Total Effort: 60 hours
Rollback: Keep Railway running during migration
```

---

**See Full Report:** [AWS_COST_OPTIMIZATION_REPORT.md](AWS_COST_OPTIMIZATION_REPORT.md)  
**Quick Reference:** [AWS_COST_QUICK_REFERENCE.md](AWS_COST_QUICK_REFERENCE.md)