# Runbook — In Case of Emergency

> For the on-call engineer. Read this at 3 AM when your brain isn't working.

---

## Alert: Service Down

**Symptoms:** `/health` returns non-200 or Prometheus alert fires.

```bash
# 1. Check containers
docker compose ps

# 2. Check app logs
docker compose logs --tail=50 app1
docker compose logs --tail=50 app2

# 3. If containers are stopped, restart
docker compose up -d

# 4. If DB is down
docker compose logs db
docker compose restart db
sleep 10
docker compose restart app1 app2
```

---

## Alert: High Error Rate (>5%)

```bash
# Check recent errors
docker compose logs app1 | grep '"levelname": "ERROR"'

# Check DB connections
docker compose exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# Restart app instances
docker compose restart app1 app2
```

---

## Alert: High Latency (p95 > 3s)

```bash
# Check DB slow queries
docker compose exec db psql -U postgres -d hackathon_db \
  -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 5;"

# Check system resources
top
free -h
df -h
```

---

## Database: Restore from Backup

```bash
# Backup
docker compose exec db pg_dump -U postgres hackathon_db > backup.sql

# Restore
cat backup.sql | docker compose exec -T db psql -U postgres hackathon_db
```

---

## Failure Modes

| Failure | Impact | Detection | Resolution |
|---------|--------|-----------|------------|
| App container crashes | 50% traffic (other instance handles it) | Prometheus alert, `docker ps` | `docker compose restart app1` |
| Both app containers crash | Full outage | `/health` returns 503 | `docker compose up -d` |
| DB down | Full outage | `/health` returns `{"db": "error"}` | `docker compose restart db` |
| Nginx down | Full outage, direct port 5000 works | Port 80 refuses connection | `docker compose restart nginx` |
| Disk full | Crash / DB corruption | `df -h` | `docker system prune -f` |
| OOM | Container kill | `dmesg \| grep -i oom` | Enable/increase swap |

---

## Contacts

- Joel Emmanuel — @JoelEmmanuelCloud
- Godwin Alexander — @maxiggle
- MLH Discord: `#pe-hackathon` channel
