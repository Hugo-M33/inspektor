# Inspektor FastAPI Server

LLM-powered natural language to SQL conversion server using LangChain and Ollama.

## Setup

### Prerequisites

- Python 3.10+
- Ollama installed and running locally
- Mistral 7B model pulled: `ollama pull mistral:7b`

### Installation

```bash
cd server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and adjust if needed:

```bash
cp .env.example .env
```

Default configuration:
- Ollama: http://localhost:11434
- Model: mistral:7b
- Server: http://127.0.0.1:8000

### Running

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## API Endpoints

### `GET /health`
Health check endpoint.

### `POST /query`
Process a natural language query.

**Request:**
```json
{
  "database_id": "my-postgres-db",
  "query": "Show me all users who signed up last month",
  "conversation_history": []
}
```

**Response (Metadata Request):**
```json
{
  "status": "needs_metadata",
  "metadata_request": {
    "request_id": "unique-id",
    "metadata_type": "tables",
    "params": {},
    "reason": "I need to know which tables are available in the database"
  }
}
```

**Response (SQL Ready):**
```json
{
  "status": "ready",
  "sql_response": {
    "sql": "SELECT * FROM users WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')",
    "explanation": "This query selects all users created in the last month",
    "confidence": "high"
  }
}
```

### `POST /metadata`
Submit metadata from the client.

**Request:**
```json
{
  "request_id": "my-postgres-db",
  "metadata_type": "tables",
  "data": {
    "tables": ["users", "posts", "comments"]
  }
}
```

### `POST /error-feedback`
Submit SQL execution errors for correction.

**Request:**
```json
{
  "database_id": "my-postgres-db",
  "sql": "SELECT * FROM user",
  "error_message": "relation \"user\" does not exist",
  "original_query": "Show me all users"
}
```

### `DELETE /cache/{database_id}`
Clear cached metadata for a database.

### `GET /cache/{database_id}`
Retrieve cached metadata for a database.

## Architecture

### Components

1. **main.py** - FastAPI application with endpoints
2. **agent.py** - LangChain agent for SQL generation
3. **cache.py** - In-memory metadata cache with TTL

### Workflow

1. Client sends natural language query
2. Agent checks cached metadata
3. If insufficient metadata, requests more from client
4. Client gathers metadata and sends back
5. Agent generates SQL when ready
6. If SQL fails, client sends error feedback
7. Agent attempts correction

## Development

### Testing the API

Use curl or httpie:

```bash
# Health check
curl http://localhost:8000/health

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "database_id": "test-db",
    "query": "Show all tables",
    "conversation_history": []
  }'
```

### Interactive API Docs

FastAPI provides interactive documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
