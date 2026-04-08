# Deployment Guide — DigitalOcean Droplet

## 1. Provision Droplet

1. Sign up at https://mlh.link/digitalocean-signup ($200 free credits)
2. Create → Droplet → Ubuntu 22.04 LTS
3. Choose the smallest allowed size (1 vCPU / 1GB RAM)
4. Pick closest datacenter
5. Name it: `TeamName-Droplet`
6. Set a root password

## 2. First Login

```bash
ssh root@<DROPLET_IP>

# Update packages
apt update && apt upgrade -y

# If RAM is limited, add swap (virtual memory)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Install Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
```

## 3. Deploy the App

```bash
# Clone repo
git clone https://github.com/JoelEmmanuelCloud/pe-hackathon/pe-hackathon-2026.git /opt/pe-hackathon
cd /opt/pe-hackathon

# Configure environment
cp .env.example .env
# Edit .env: set DB_PASSWORD to something secure

# Copy seed files
mkdir -p data
# Upload users.csv, urls.csv, events.csv to /opt/pe-hackathon/data/

# Start everything
docker compose up -d --build

# Load seed data
docker compose exec app1 uv run scripts/load_csv.py data/

# Verify
curl http://localhost/health
```

## 4. Set GitHub Secrets for CI/CD

In your GitHub repo → Settings → Secrets → Actions:

| Secret | Value |
|--------|-------|
| `DROPLET_IP` | Your droplet's public IP |
| `DROPLET_PASSWORD` | Your droplet's root password |

After this, every push to `main` will auto-deploy.

## 5. Rollback

```bash
cd /opt/pe-hackathon
git log --oneline -5      # Find the last good commit hash
git checkout <hash>
docker compose up -d --build
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| App won't start | `docker compose logs app1` |
| DB connection refused | `docker compose ps db` — check if healthy |
| Port 80 in use | `lsof -i :80` then `kill <PID>` |
| Out of memory | Check swap is active: `free -h` |
