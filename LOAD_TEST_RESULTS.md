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

## Results

| Metric | Value |
|--------|-------|
| Total requests | 5456 |
| Error rate | 1.68% |
| p(50) latency | 1.94s |
| p(90) latency | 10.5s |
| p(95) latency | 11.84s |
| Avg latency | 4.19s |

## Thresholds

| Threshold | Status |
|-----------|--------|
| error rate < 5% | PASS |
| p(95) < 3000ms | FAIL |

## Bottleneck Analysis

The bottleneck is CPU and RAM on the 512MB/1 vCPU droplet. Under 200 concurrent
users each making 4 requests (health, list URLs, shorten, redirect), the PostgreSQL
query load and Flask worker saturation caused latency to spike above 3 seconds.

The fix would be: add Redis caching on the `/urls` list endpoint and the redirect
lookup to eliminate repeated DB hits. The redirect endpoint (most frequent) would
benefit most — a cache hit avoids a full DB query per click.

## Scalability Architecture

- 2x Flask app instances behind Nginx (horizontal scaling)
- Nginx round-robin load balancing
- PostgreSQL shared DB
- Redis available (not yet used for caching)
