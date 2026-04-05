# Failure Mode Documentation

## What happens when things break?

### 1. Invalid Input → Graceful JSON error

**Scenario:** User sends `POST /shorten` without `original_url`.

**Response:**
```json
HTTP 400 Bad Request
{"error": "original_url is required"}
```
The app never crashes. All validation returns structured JSON with an appropriate HTTP status code.

### 2. Unknown Short Code → 404

**Scenario:** `GET /notexist` where `notexist` is not in the DB.

**Response:**
```json
HTTP 404 Not Found
{"error": "URL not found"}
```

### 3. Inactive URL → 410 Gone

**Scenario:** `GET /abc123` where the URL has been deactivated.

**Response:**
```json
HTTP 410 Gone
{"error": "URL is no longer active"}
```
Data is preserved in DB. Reactivation is possible via a direct DB update.

### 4. DB Connection Lost → 503

**Scenario:** PostgreSQL goes down mid-request.

**Response from `/health`:**
```json
HTTP 503 Service Unavailable
{"status": "degraded", "db": "error"}
```
The load balancer stops routing to this instance (if health checks are configured).

### 5. Container crash → Auto-restart

**Scenario:** App process crashes (OOM, unhandled exception).

**Resolution:** Docker `restart: always` policy brings the container back within seconds. The second app instance (app2) continues handling traffic during restart.

### 6. Chaos Test: Kill app1

```bash
docker compose stop app1
# → All traffic routes to app2 via Nginx
# → app1 restarts automatically due to restart policy
docker compose ps  # shows app1 restarting
```
