# Inspektor Server Deployment Guide

This guide covers deploying the Inspektor LLM server with Ollama and Mistral 7B using Docker Compose.

## Prerequisites

- **Docker** 20.10+ ([install guide](https://docs.docker.com/get-docker/))
- **Docker Compose** 2.0+ (included with Docker Desktop)
- **8GB+ RAM** (16GB recommended for Mistral 7B)
- **20GB+ disk space** (for Ollama models)
- **GPU** (optional but recommended for better performance)

### For GPU Support (NVIDIA)

Install NVIDIA Docker runtime:

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

## Quick Start

### 1. Clone and Navigate to Project

```bash
cd /path/to/inspektor
```

### 2. Start All Services

```bash
docker compose up -d
```

This will:
1. Start Ollama service
2. Pull Mistral 7B model (first time only, ~4GB download)
3. Start the Inspektor FastAPI server
4. Set up networking between services

### 3. Check Status

```bash
# View logs
docker compose logs -f

# Check service health
docker compose ps

# Verify Ollama is running
curl http://localhost:11434/api/tags

# Verify Inspektor server is running
curl http://localhost:8000/health
```

### 4. Stop Services

```bash
docker compose down
```

To remove volumes (model data will be deleted):
```bash
docker compose down -v
```

## Configuration

### CPU vs GPU

**CPU-only (default):** Works out of the box but slower inference

**GPU-enabled:** Edit `docker-compose.yml` and uncomment the GPU section:

```yaml
ollama:
  # Uncomment for GPU support
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

Then restart:
```bash
docker compose down
docker compose up -d
```

### Environment Variables

Edit the `inspektor-server` service environment in `docker-compose.yml`:

```yaml
environment:
  - OLLAMA_BASE_URL=http://ollama:11434  # Ollama service URL
  - OLLAMA_MODEL=mistral:7b               # Model to use
  - HOST=0.0.0.0                          # Bind address
  - PORT=8000                             # Server port
```

### Using Different Models

To use a different Ollama model:

1. Edit `docker-compose.yml`:
```yaml
ollama-pull-mistral:
  command:
    - |
      ollama pull llama3:8b  # Change model here
```

2. Update server environment:
```yaml
inspektor-server:
  environment:
    - OLLAMA_MODEL=llama3:8b  # Match model name
```

3. Restart:
```bash
docker compose down
docker compose up -d
```

## Production Deployment

### Security Recommendations

1. **Use secrets for sensitive data:**
```yaml
secrets:
  db_password:
    file: ./secrets/db_password.txt

services:
  inspektor-server:
    secrets:
      - db_password
```

2. **Enable HTTPS with reverse proxy:**
```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
```

3. **Limit container resources:**
```yaml
inspektor-server:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
      reservations:
        cpus: '1'
        memory: 2G
```

### Scaling

**Run multiple server instances:**

```bash
docker compose up -d --scale inspektor-server=3
```

**Add load balancer:**
```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    depends_on:
      - inspektor-server
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
```

### Monitoring

**Add health check endpoints:**

```bash
# Ollama health
curl http://localhost:11434/api/tags

# Server health
curl http://localhost:8000/health

# Check logs
docker compose logs --tail=100 -f inspektor-server
```

**Container stats:**
```bash
docker stats inspektor-ollama inspektor-server
```

### Backup and Restore

**Backup Ollama models:**
```bash
docker run --rm -v inspektor_ollama_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/ollama-backup.tar.gz /data
```

**Restore Ollama models:**
```bash
docker run --rm -v inspektor_ollama_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/ollama-backup.tar.gz -C /
```

## Troubleshooting

### Ollama fails to start

**Issue:** Container exits immediately

**Solution:** Check logs and ensure enough disk space
```bash
docker compose logs ollama
df -h
```

### Mistral model won't download

**Issue:** `ollama-pull-mistral` service fails

**Solution:** Check network and retry
```bash
# Manual pull
docker exec -it inspektor-ollama ollama pull mistral:7b

# Check progress
docker compose logs ollama-pull-mistral
```

### Server can't connect to Ollama

**Issue:** Connection refused to Ollama

**Solution:** Ensure Ollama is healthy
```bash
docker compose ps
docker compose restart ollama
docker exec -it inspektor-ollama ollama list
```

### Out of memory errors

**Issue:** Container killed due to OOM

**Solution:** Increase Docker memory limit or use smaller model
```bash
# Check memory usage
docker stats

# Use smaller model
OLLAMA_MODEL=mistral:7b-instruct-q4_0  # Quantized version
```

### Slow inference times

**Issue:** Queries take too long

**Solutions:**
1. Enable GPU support (see Configuration section)
2. Use quantized model (smaller, faster)
3. Increase `OLLAMA_NUM_PARALLEL`
4. Add more RAM to Docker

## Performance Tuning

### Ollama Environment Variables

```yaml
environment:
  - OLLAMA_NUM_PARALLEL=4       # Concurrent requests
  - OLLAMA_MAX_LOADED_MODELS=1  # Models in memory
  - OLLAMA_FLASH_ATTENTION=1    # Enable flash attention
  - OLLAMA_NUM_GPU=1            # GPUs to use
```

### Server Workers

Adjust Uvicorn workers in Dockerfile:
```dockerfile
CMD ["uvicorn", "main_improved:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Resource Allocation

```yaml
ollama:
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 12G
      reservations:
        cpus: '2'
        memory: 8G
```

## Connecting the Tauri Client

Update the Tauri client to connect to the Docker server:

```typescript
// client/src/services/llm-improved.ts
const API_BASE_URL = 'http://localhost:8000';  // Docker host
```

Or for remote deployment:
```typescript
const API_BASE_URL = process.env.VITE_API_URL || 'http://localhost:8000';
```

Then set environment variable:
```bash
export VITE_API_URL=https://your-server.com
cd client
npm run tauri dev
```

## Cloud Deployment

### Docker Hub

```bash
# Build and push
docker build -t yourusername/inspektor-server:latest ./server
docker push yourusername/inspektor-server:latest

# Update docker-compose.yml
services:
  inspektor-server:
    image: yourusername/inspektor-server:latest
```

### AWS ECS / Google Cloud Run / Azure Container Instances

Use the provided `docker-compose.yml` as reference for container configuration.

**Key considerations:**
- Persistent volume for Ollama models
- GPU instance types for better performance
- Load balancer for multiple server instances
- Auto-scaling based on CPU/memory

## Development vs Production

### Development (Current Setup)
```bash
docker compose up -d
# Fast iteration, all logs visible
```

### Production
```bash
# Use production compose file
docker compose -f docker-compose.prod.yml up -d

# With environment file
docker compose --env-file .env.production up -d

# With specific resources
docker compose up -d --scale inspektor-server=3
```

## Useful Commands

```bash
# Rebuild after code changes
docker compose build inspektor-server
docker compose up -d inspektor-server

# View specific service logs
docker compose logs -f inspektor-server

# Execute command in container
docker exec -it inspektor-server bash

# Pull new Ollama model
docker exec -it inspektor-ollama ollama pull llama3:8b

# List running models
docker exec -it inspektor-ollama ollama list

# Remove all containers and volumes
docker compose down -v

# Prune unused Docker resources
docker system prune -a
```

## FAQ

**Q: Can I run this without Docker?**
A: Yes, follow the manual setup in [README.md](README.md)

**Q: How much RAM do I need?**
A: Minimum 8GB, recommended 16GB for Mistral 7B

**Q: Does it support Apple Silicon (M1/M2/M3)?**
A: Yes, Ollama has native ARM support

**Q: Can I use OpenAI instead of Ollama?**
A: Yes, modify `agent_improved.py` to use OpenAI's API

**Q: How do I persist the cache?**
A: Schema cache is in-memory. For persistence, implement Redis or database backend

**Q: Can I use multiple GPUs?**
A: Yes, set `OLLAMA_NUM_GPU=2` and adjust Docker GPU config

## Support

For issues:
- Check logs: `docker compose logs -f`
- Verify health: `docker compose ps`
- GitHub Issues: [your-repo/issues](https://github.com/yourrepo/issues)
- Ollama docs: https://ollama.ai/docs

## License

MIT License - see [LICENSE](LICENSE)
