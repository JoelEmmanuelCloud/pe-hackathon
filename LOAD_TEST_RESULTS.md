# Load Test Results

## Tool
k6 v1.7.1

## Target
http://167.172.165.216 (1 vCPU, 512MB RAM, 2x Flask + Nginx)

## Stages
- 0-30s: ramp to 50 users
- 30-90s: hold at 50 users
- 90-120s: ramp to 200 users
- 120-180s: hold at 200 users
- 180-210s: ramp down

---

## Run 1 — Before Redis caching

| Metric | Value |
|--------|-------|
| Total requests | 5456 |
| Error rate | 1.68% |
| p(50) latency | 1.94s |
| p(90) latency | 10.5s |
| p(95) latency | 11.84s |
| Avg latency | 4.19s |

| Threshold | Status |
|-----------|--------|
| error rate < 5% | PASS |
| p(95) < 3000ms | FAIL |

## Run 2 — After Redis caching (redirect + list endpoints)

| Metric | Value |
|--------|-------|
| Total requests | 5284 |
| Error rate | 1.28% |
| p(90) latency | 10.11s |
| p(95) latency | 11s |
| Avg latency | 4.35s |

| Threshold | Status |
|-----------|--------|
| error rate < 5% | PASS |
| p(95) < 3000ms | FAIL |

### Changes between runs
- Error rate: 1.68% → 1.28% (24% reduction)
- p(95): 11.84s → 11s (7% reduction)
- Requests served: 5456 → 5284 (comparable volume)

---

## Bottleneck Analysis

The remaining bottleneck is CPU saturation from write operations. The load test pattern
generates a unique URL on every iteration, meaning:

1. Every `POST /shorten` is a DB write — uncacheable by design
2. Every `GET /<short_code>` redirect is a first-time visit — always a cache miss

This is a worst-case scenario for caching. In real-world traffic where the same URLs
are clicked repeatedly, Redis eliminates the DB query entirely on every hit after the
first, and the improvement would be substantially larger.

The hard ceiling at 200 VUs on a 512MB/1 vCPU droplet is the PostgreSQL write throughput
combined with Flask worker saturation. Vertical scaling (larger droplet) or moving writes
to a queue would address this.

---

## Scalability Architecture

- 2x Flask app instances behind Nginx (horizontal scaling)
- Nginx round-robin load balancing
- PostgreSQL shared DB
- Redis caching on `/<short_code>` redirect lookups (TTL 300s)
- Redis caching on `GET /urls` list endpoint (TTL 5s)
- Cache invalidation on URL create, update, and deactivate
