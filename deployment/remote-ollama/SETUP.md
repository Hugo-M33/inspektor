# Remote Ollama Setup Guide

This guide helps you deploy Ollama on a remote server and access it from your local development environment.

## Prerequisites

- Remote server with Docker installed
- Nginx already running on the server
- SSH access to the server
- Domain or IP address with SSL certificate (recommended)

## Setup Steps

### 1. Deploy Ollama on Remote Server

SSH into your remote server and deploy Ollama:

```bash
# Copy docker-compose.yml to your server
scp deployment/remote-ollama/docker-compose.yml user@your-server.com:~/ollama/

# SSH into server
ssh user@your-server.com

# Navigate to directory and start Ollama
cd ~/ollama
docker compose up -d

# Verify Ollama is running
docker compose logs -f
```

Wait for the model to download. You should see:
```
Model pulled successfully! You can now use: llama3.2:1b
```

### 2. Configure Nginx Proxy

Add the Ollama proxy configuration to your existing nginx setup:

```bash
# Copy nginx config to server
scp deployment/remote-ollama/nginx-ollama.conf user@your-server.com:/tmp/

# SSH into server
ssh user@your-server.com

# Add config to your nginx server block
sudo nano /etc/nginx/sites-available/your-domain

# Paste the contents of nginx-ollama.conf inside your server block
# Or include it:
# include /etc/nginx/snippets/ollama.conf;

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### 3. Test Remote Connection

Verify Ollama is accessible through nginx:

```bash
# From your local machine
curl https://your-server.com/ollama/api/tags

# Should return JSON with available models:
# {"models":[{"name":"llama3.2:1b",...}]}
```

### 4. Update Local Environment

Update your local `.env` file to use the remote Ollama:

```bash
# server/.env
OLLAMA_BASE_URL=https://your-server.com/ollama
OLLAMA_MODEL=llama3.2:1b
```

### 5. Start Local Development

```bash
# Start only the FastAPI server locally
# (Ollama runs remotely now)
cd server
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Verification

Test the complete setup:

```bash
# Check Ollama connectivity
curl https://your-server.com/ollama/api/tags

# Check server health
curl http://localhost:8000/health

# Test query (should work with remote Ollama)
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "database_id": "test",
    "query": "Show me all users"
  }'
```

## Managing Models

Pull additional models on your remote server:

```bash
# SSH into server
ssh user@your-server.com

# Pull mistral 7b for production
docker exec ollama ollama pull mistral:7b

# List all models
docker exec ollama ollama list

# Remove a model
docker exec ollama ollama rm llama3.2:1b
```

## Troubleshooting

### Connection Refused

- Check Ollama is running: `docker ps | grep ollama`
- Check nginx proxy: `sudo nginx -t && sudo systemctl status nginx`
- Check firewall allows HTTPS: `sudo ufw status`

### Model Not Found

- Verify model is pulled: `docker exec ollama ollama list`
- Check logs: `docker compose logs ollama`

### Slow Performance

- Use smaller model for dev: `llama3.2:1b` (~1GB)
- Use faster model: `llama3.2:3b` (~2GB) as middle ground
- Check server resources: `docker stats ollama`

### SSL/HTTPS Issues

If you don't have SSL yet, you can use HTTP temporarily for testing:

```env
# server/.env (INSECURE - for testing only!)
OLLAMA_BASE_URL=http://your-server.com/ollama
```

For production, use Let's Encrypt:
```bash
sudo certbot --nginx -d your-server.com
```

## Architecture

```
┌─────────────────┐
│  Local Dev Env  │
│                 │
│  Tauri Client   │
│       +         │
│  FastAPI Server │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│  Remote Server  │
│                 │
│  Nginx :443     │
│       │         │
│       ▼         │
│  Ollama :11434  │
│  (llama3.2:1b)  │
└─────────────────┘
```

## Benefits

- **Faster Local Dev**: No LLM running on your slow PC
- **Consistent Performance**: Server-grade hardware for model inference
- **Shared Resources**: Multiple developers can use same Ollama instance
- **Easy Scaling**: Upgrade server or add GPU without changing client code

## Security Notes

- Ollama only listens on `127.0.0.1:11434` (not exposed to internet)
- Nginx handles SSL/TLS termination
- Only `/ollama/` path is proxied
- Database credentials never sent to server (still client-side only!)

## Cost Estimates

Running llama3.2:1b on a VPS:
- **CPU-only**: $5-10/month (2 vCPU, 4GB RAM) - Slower inference
- **GPU**: $20-50/month (basic GPU) - Fast inference

For production with mistral:7b, consider 8GB+ RAM and GPU.
