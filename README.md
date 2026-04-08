# PE Hackathon — URL Shortener

A production-grade URL shortener built for the MLH Production Engineering Hackathon 2026.

**Stack:** Flask · Peewee ORM · PostgreSQL · Docker · Nginx · Prometheus · Grafana

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
cd pe-hackathon-2026

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

---

## Running Tests

```bash
uv run pytest --cov=app --cov-report=term-missing
```

---

## Deploy to DigitalOcean Droplet

See [DEPLOY.md](DEPLOY.md).

---

## Monitoring

- **Prometheus:** `http://<droplet-ip>:9090`
- **Grafana:** `http://<droplet-ip>:3000` (admin/admin)

Import the dashboard via Grafana UI → Dashboards → Import → paste dashboard JSON.
