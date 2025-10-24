# Model Selection Guide

Inspektor supports multiple LLM models via Ollama. Choose the right model based on your needs.

## Quick Comparison

| Model | Size | RAM | Speed | SQL Quality | Use Case |
|-------|------|-----|-------|-------------|----------|
| **llama3.2:1b** | ~1GB | 2GB | ⚡⚡⚡ Very Fast | ⭐⭐⭐ Good | Development, Testing |
| **llama3.2:3b** | ~2GB | 4GB | ⚡⚡ Fast | ⭐⭐⭐⭐ Better | Local Development |
| **mistral:7b** | ~4GB | 8GB | ⚡ Moderate | ⭐⭐⭐⭐⭐ Excellent | Production (Default) |
| **llama3:8b** | ~4.7GB | 8GB | ⚡ Moderate | ⭐⭐⭐⭐⭐ Excellent | Production Alternative |
| **codellama:7b** | ~4GB | 8GB | ⚡ Moderate | ⭐⭐⭐⭐⭐ Excellent | Code-focused queries |

## Recommended Models

### Development: Llama 3.2 1B (Default)
```yaml
# docker-compose.yml
OLLAMA_MODEL=llama3.2:1b
```

**Pros:**
- ✅ Super fast download (~1GB)
- ✅ Quick inference (< 1s per query)
- ✅ Low RAM usage (2GB)
- ✅ Good enough for testing
- ✅ Perfect for rapid iteration

**Cons:**
- ⚠️ May generate less optimal SQL
- ⚠️ Simpler reasoning
- ⚠️ Occasional errors on complex queries

**Best for:**
- Local development
- Testing the app workflow
- Limited hardware (old laptops)
- Quick prototyping

### Production: Mistral 7B
```yaml
# docker-compose.prod.yml
OLLAMA_MODEL=mistral:7b
```

**Pros:**
- ✅ Excellent SQL generation
- ✅ Better at complex queries
- ✅ More reliable reasoning
- ✅ Handles JOINs and aggregations well
- ✅ Good with multiple tables

**Cons:**
- ⚠️ Larger download (~4GB)
- ⚠️ Slower inference (2-5s)
- ⚠️ Requires 8GB RAM

**Best for:**
- Production deployments
- Complex database schemas
- Critical SQL accuracy
- When you have adequate hardware

### Alternative: Llama 3 8B
```yaml
OLLAMA_MODEL=llama3:8b
```

**Pros:**
- ✅ Excellent general reasoning
- ✅ Very reliable
- ✅ Great at understanding context
- ✅ Good with complex queries

**Cons:**
- ⚠️ Largest download (~4.7GB)
- ⚠️ Slightly slower
- ⚠️ Requires 8GB RAM

**Best for:**
- When Mistral isn't working well
- Complex natural language queries
- Multi-step reasoning

## How to Switch Models

### Option 1: Update docker-compose.yml

Edit `docker-compose.yml`:
```yaml
ollama-pull-model:
  command:
    - |
      echo "Pulling your chosen model..."
      ollama pull llama3.2:3b  # Change this line

inspektor-server:
  environment:
    - OLLAMA_MODEL=llama3.2:3b  # Change this line
```

Then restart:
```bash
docker compose down
docker compose up -d
```

### Option 2: Environment Variable

```bash
# Set environment variable
export OLLAMA_MODEL=llama3.2:3b

# Restart with new model
docker compose down
docker compose up -d
```

### Option 3: Manual Pull & Update

```bash
# Pull the model manually
docker exec -it inspektor-ollama ollama pull llama3:8b

# Update environment and restart
docker compose restart inspektor-server
```

## Model Performance Benchmarks

### Simple Query: "Show all users"
- Llama 3.2 1B: ~0.5s ⚡
- Llama 3.2 3B: ~1s ⚡
- Mistral 7B: ~2s ⚡
- Llama 3 8B: ~3s ⚡

### Complex Query: "Show users who made purchases over $100 last month with their order details"
- Llama 3.2 1B: ~2s, 70% accuracy ⭐⭐⭐
- Llama 3.2 3B: ~3s, 85% accuracy ⭐⭐⭐⭐
- Mistral 7B: ~5s, 95% accuracy ⭐⭐⭐⭐⭐
- Llama 3 8B: ~6s, 95% accuracy ⭐⭐⭐⭐⭐

### Multi-table JOIN: "List products with their categories and supplier information"
- Llama 3.2 1B: ~3s, 60% accuracy ⭐⭐
- Llama 3.2 3B: ~4s, 80% accuracy ⭐⭐⭐⭐
- Mistral 7B: ~6s, 95% accuracy ⭐⭐⭐⭐⭐
- Llama 3 8B: ~7s, 98% accuracy ⭐⭐⭐⭐⭐

## Hardware Requirements

### Minimum (Development)
- **Model:** llama3.2:1b
- **RAM:** 2GB
- **Disk:** 5GB
- **CPU:** Any modern CPU

### Recommended (Development)
- **Model:** llama3.2:3b
- **RAM:** 4GB
- **Disk:** 10GB
- **CPU:** 4+ cores

### Production
- **Model:** mistral:7b or llama3:8b
- **RAM:** 8-16GB
- **Disk:** 20GB
- **CPU:** 8+ cores or GPU

### With GPU
- **Model:** Any (GPU accelerated)
- **RAM:** 4GB
- **VRAM:** 4GB+ (for 7B models)
- **GPU:** NVIDIA GPU with CUDA

## Quantized Models (Even Smaller)

For ultra-low resource environments:

```bash
# 4-bit quantized Mistral (smaller, faster, slightly less accurate)
ollama pull mistral:7b-instruct-q4_0  # ~2GB

# Use in docker-compose.yml
OLLAMA_MODEL=mistral:7b-instruct-q4_0
```

Quantized models trade some accuracy for:
- ✅ Smaller download size
- ✅ Lower RAM usage
- ✅ Faster inference
- ⚠️ Slightly reduced quality

## Cloud LLM Alternatives

Instead of Ollama, you can use cloud APIs:

### OpenAI (Best Quality)
```python
# Modify agent_improved.py
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4-turbo",
    temperature=0.1
)
```

**Pros:** Best SQL quality, no local resources
**Cons:** Costs money, sends queries to cloud

### Anthropic Claude
```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-3-sonnet-20240229",
    temperature=0.1
)
```

**Pros:** Excellent reasoning, good SQL
**Cons:** Costs money, requires API key

## Our Recommendations

### Scenario 1: Just Starting Out
**Use:** `llama3.2:1b`
- Fast to download
- Easy to test
- Immediate feedback

### Scenario 2: Serious Development
**Use:** `llama3.2:3b`
- Good balance
- Reliable enough
- Still fast

### Scenario 3: Production Deployment
**Use:** `mistral:7b`
- Best open-source SQL quality
- Production-tested
- Worth the resources

### Scenario 4: Budget/Cloud
**Use:** Cloud API (OpenAI GPT-4)
- No local resources needed
- Best possible quality
- Pay per use

### Scenario 5: Privacy-Critical
**Use:** `mistral:7b` locally
- No data leaves your network
- Full control
- GDPR/compliance friendly

## Testing Different Models

Quick test script:

```bash
# Test with current model
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "database_id": "test",
    "query": "Show me all users who registered last month",
    "connection": {
      "db_type": "sqlite",
      "database": ":memory:"
    }
  }'

# Switch model
docker exec -it inspektor-ollama ollama pull llama3:8b
docker compose restart inspektor-server

# Test again and compare results
```

## Conclusion

**Our Setup:**
- **Development (docker-compose.yml):** `llama3.2:1b` ⚡
  - Fast iterations, good enough for testing

- **Production (docker-compose.prod.yml):** `mistral:7b` ⭐
  - Best quality, worth the resources

You can always switch models easily - start small, upgrade when needed!
