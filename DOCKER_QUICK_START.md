# Docker Quick Start Guide

Get Inspektor running with Docker in under 5 minutes!

## Prerequisites

- Docker Desktop installed ([download](https://www.docker.com/products/docker-desktop))
- 20GB free disk space (for Mistral 7B model)
- 8GB+ RAM

## Quick Start

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd inspektor

# 2. Start everything
docker compose up -d

# 3. Check status
docker compose ps
```

That's it! Access the server at `http://localhost:8000`.

## First Time Setup

On first run, Docker will:
1. ✓ Pull Ollama image (~1GB)
2. ✓ Build Inspektor server image
3. ✓ Download Mistral 7B model (~4GB)
4. ✓ Start all services

This takes 5-10 minutes depending on your internet speed.

## Common Commands

### Start Services
```bash
# Foreground (with logs)
docker compose up

# Background
docker compose up -d

# With Makefile
make dev-up
```

### Stop Services
```bash
docker compose down

# Or
make dev-down
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f inspektor-server

# Last 100 lines
docker compose logs --tail=100
```

### Check Health
```bash
# Ollama
curl http://localhost:11434/api/tags

# Server
curl http://localhost:8000/health

# Or use Makefile
make health
```

### Restart Services
```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart inspektor-server
```

## Troubleshooting

### "Connection refused" when accessing server

**Solution:** Wait for all services to be healthy
```bash
docker compose ps
# All services should show "healthy"
```

### Mistral model not downloading

**Solution:** Check logs and manually pull
```bash
docker compose logs ollama-pull-mistral

# Manual pull
docker exec -it inspektor-ollama ollama pull mistral:7b
```

### Out of disk space

**Solution:** Clean up Docker
```bash
docker system df        # Check usage
docker system prune     # Clean unused
docker volume ls        # List volumes
```

### Services keep restarting

**Solution:** Check logs for errors
```bash
docker compose logs --tail=50
```

## Using Different Models

### Llama 3
```bash
# Pull model
docker exec -it inspektor-ollama ollama pull llama3:8b

# Update docker-compose.yml
# Change: OLLAMA_MODEL=llama3:8b

# Restart
docker compose restart inspektor-server
```

### CodeLlama
```bash
docker exec -it inspektor-ollama ollama pull codellama:7b

# Update environment and restart
```

### List Available Models
```bash
docker exec -it inspektor-ollama ollama list
```

## Development Workflow

### Code Changes

```bash
# After changing server code
docker compose build inspektor-server
docker compose up -d inspektor-server

# Or with Makefile
make rebuild
```

### View Server Shell
```bash
docker exec -it inspektor-server /bin/bash
```

### View Ollama Shell
```bash
docker exec -it inspektor-ollama /bin/bash
```

## Resource Usage

### Check Resource Consumption
```bash
docker stats

# Or with Makefile
make stats
```

### Limit Resources

Edit `docker-compose.yml`:
```yaml
inspektor-server:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
```

## Production Deployment

For production with load balancing and SSL:

```bash
# Use production compose file
docker compose -f docker-compose.prod.yml up -d

# Or with Makefile
make prod-up
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for full production guide.

## Cleanup

### Stop and Remove Everything
```bash
docker compose down

# With Makefile
make clean
```

### Remove Volumes (Deletes Model)
```bash
docker compose down -v

# WARNING: This deletes the 4GB Mistral model!
```

### Full Docker Cleanup
```bash
docker system prune -a

# Or with Makefile
make prune-all
```

## Advanced

### GPU Support

Uncomment GPU section in `docker-compose.yml`:
```yaml
ollama:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

Requires: nvidia-docker runtime

### Scale Server Instances
```bash
docker compose up -d --scale inspektor-server=3
```

### Custom Network Port
```bash
# Edit docker-compose.yml
ports:
  - "9000:8000"  # Host:Container
```

## Environment Variables

Create `.env` file:
```bash
OLLAMA_MODEL=mistral:7b
OLLAMA_NUM_PARALLEL=4
```

Use in `docker-compose.yml`:
```yaml
environment:
  - OLLAMA_MODEL=${OLLAMA_MODEL}
```

## Makefile Commands

```bash
make help          # Show all commands
make dev-up        # Start development
make dev-down      # Stop development
make dev-logs      # View logs
make health        # Check health
make status        # Container status
make stats         # Resource usage
make backup        # Backup Ollama models
make pull-model    # Pull Mistral manually
make clean         # Stop and clean
```

## Connecting the Client

The Tauri client connects to `http://localhost:8000` by default.

For remote server:
```typescript
// client/src/services/llm-improved.ts
const API_BASE_URL = 'http://your-server.com:8000';
```

## Getting Help

- Check logs: `docker compose logs -f`
- Check status: `docker compose ps`
- Check health: `make health`
- See full guide: [DEPLOYMENT.md](DEPLOYMENT.md)

## Next Steps

1. ✅ Server running? → Connect with Tauri client
2. ✅ Want production deployment? → See [DEPLOYMENT.md](DEPLOYMENT.md)
3. ✅ Want to contribute? → See [CONTRIBUTING.md](CONTRIBUTING.md)
4. ✅ Found a bug? → Open an issue on GitHub

Happy querying! 🚀
