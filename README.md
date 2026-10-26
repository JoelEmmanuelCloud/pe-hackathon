# PE Hackathon — URL Shortener

A production-grade URL shortener built solo by Joel Emmanuel for the MLH Production Engineering Hackfest 2026, to practice SRE-style production engineering (observability, load testing, graceful failure) rather than just application logic.

**Stack:** Flask · Peewee ORM · PostgreSQL · Redis · Docker · Nginx · Prometheus · Grafana

---

## Architecture

```
Internet → Nginx (port 80)
               ├── app1 (Flask, port 5000)
               └── app2 (Flask, port 5000)
                        └── PostgreSQL (port 5432)
                        └── Redis (port 6379)

Monitoring: Prometheus (9090) → Grafana (3000)
```

---

## Quick Start (Local)

**Prerequisites:** Python 3.12+, `uv`, PostgreSQL

```bash
# 1. Clone & enter
git clone https://github.com/JoelEmmanuelCloud/pe-hackathon
cd pe-hackathon

# 2. Install deps
uv sync --extra dev

# 3. Configure environment
cp .env.example .env
# Edit .env with your Postgres credentials

# 4. Create tables & load seed data
createdb hackathon_db
uv run scripts/load_csv.py data/

# 5. Run server
uv run run.py

# 6. Verify
curl http://localhost:5000/health
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/shorten` | Create a short URL |
| `GET` | `/<short_code>` | Redirect to original URL |
| `GET` | `/urls` | List all URLs (paginated) |
| `GET` | `/urls/<id>` | Get URL by ID |
| `DELETE` | `/urls/<id>` | Deactivate a URL |
| `GET` | `/stats/<short_code>` | Click stats for a URL |
| `GET` | `/users` | List users |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Prometheus metrics |

### POST /shorten

```json
// Request
{
  "original_url": "https://example.com/very/long/url",
  "title": "My Link",
  "user_id": 1
}

// Response 201
{
  "id": 42,
  "short_code": "aB3xYz",
  "original_url": "https://example.com/very/long/url",
  "title": "My Link",
  "is_active": true,
  "created_at": "2026-04-05T10:00:00"
}
```

---

## Docker Deployment

```bash
# Start full stack (2 app instances + Nginx + Postgres + Prometheus + Grafana)
docker compose up -d --build

# Check containers
docker ps

# View logs
docker compose logs -f app1
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_NAME` | `hackathon_db` | PostgreSQL database name |
| `DB_USER` | `postgres` | PostgreSQL user |
| `DB_PASSWORD` | `` | PostgreSQL password |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `FLASK_ENV` | `production` | Flask environment |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `CACHE_TTL` | `300` | Redirect cache TTL in seconds |

---

## Running Tests

```bash
uv run pytest --cov=app --cov-report=term-missing
```

---

## Load Testing

Full methodology and raw results: [LOAD_TEST_RESULTS.md](LOAD_TEST_RESULTS.md).

Tested with k6 against a single DigitalOcean droplet (1 vCPU, 512MB RAM, 2x Flask + Nginx), ramping to 200 concurrent users. The test pattern generates a unique URL on every write and a first-time visit on every redirect, which is a worst-case scenario for caching (every request is a cache miss by design).

| Metric | Before Redis caching | After Redis caching | Change |
|--------|----------------------|----------------------|--------|
| Error rate | 1.68% | 1.28% | -24% |
| p(95) latency | 11.84s | 11.00s | -7% |

The p(95) < 3000ms threshold failed in both runs. The remaining bottleneck is CPU saturation from PostgreSQL write throughput and Flask worker contention under this specific worst-case access pattern, not something Redis caching addresses, since cache hits require repeated reads of the same key. In traffic with realistic repeat-read patterns, the cache would show a larger effect. See the Bottleneck Analysis section of the results file for the full breakdown.

---

## Failure Handling

Full scenario documentation: [FAILURE_MODES.md](FAILURE_MODES.md).

- **Redis unavailable:** `app/cache.py` treats any connection or operation failure as a cache miss. Reads fall through to PostgreSQL, writes are skipped, and the failure is logged. The app never raises on a Redis outage.
- **PostgreSQL unavailable:** `/health` returns `503` with `{"status": "degraded", "db": "error"}`, so a load balancer or health check can stop routing to that instance.
- **Container crash:** Docker's `restart: always` policy brings the container back automatically; the second app instance keeps serving traffic in the meantime. The chaos-test procedure (`docker compose stop app1`) is in `FAILURE_MODES.md`; general on-call steps are in `RUNBOOK.md`.

---

## Deploy to DigitalOcean Droplet

See [DEPLOY.md](DEPLOY.md).

---

## Monitoring

- **Prometheus:** `http://<droplet-ip>:9090`
- **Grafana:** `http://<droplet-ip>:3000` (admin/admin)

Import the dashboard via Grafana UI → Dashboards → Import → paste dashboard JSON.
