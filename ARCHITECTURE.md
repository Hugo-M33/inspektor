# Inspektor Architecture

## Core Security Principle

**Credentials NEVER leave the client**

This is the fundamental design principle that makes Inspektor secure and GDPR-compliant.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    TAURI CLIENT (Desktop App)                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Encrypted Credential Storage                         │   │
│  │  • PostgreSQL: postgres://user:pass@host:port/db    │   │
│  │  • MySQL: mysql://user:pass@host:port/db            │   │
│  │  • SQLite: sqlite:///path/to/db.sqlite              │   │
│  │  ✅ Never transmitted to server                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Database Operations (Rust/Tauri Commands)           │   │
│  │  • test_database_connection()                        │   │
│  │  • execute_sql_query(db_id, sql)                    │   │
│  │  • get_database_tables(db_id)                       │   │
│  │  • get_database_table_schema(db_id, table)         │   │
│  │  • get_database_relationships(db_id)                │   │
│  │  ✅ All executed locally using stored credentials    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  React Frontend                                       │   │
│  │  • ConnectionManager: Add/Test/Delete connections    │   │
│  │  • QueryInterface: Natural language input            │   │
│  │  • MetadataApproval: User approves LLM requests     │   │
│  │  • ResultsViewer: Display query results             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                         ▲ │
                         │ ▼
          Only metadata, never credentials!
                         ▲ │
                         │ ▼
┌─────────────────────────────────────────────────────────────┐
│               FASTAPI SERVER (Python/LLM)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  LLM Agent (Ollama/Mistral or Llama)                │   │
│  │  • Analyzes natural language queries                 │   │
│  │  • Requests metadata when needed                     │   │
│  │  • Generates SQL from cached metadata                │   │
│  │  • Never has database credentials                    │   │
│  │  • Never connects to user databases                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Metadata Cache (In-Memory)                          │   │
│  │  {                                                    │   │
│  │    "db-123": {                                       │   │
│  │      "tables": ["users", "orders"],                  │   │
│  │      "schemas": {                                    │   │
│  │        "users": [                                    │   │
│  │          {"name": "id", "type": "int"},             │   │
│  │          {"name": "email", "type": "varchar"}       │   │
│  │        ]                                             │   │
│  │      },                                              │   │
│  │      "relationships": [...]                          │   │
│  │    }                                                 │   │
│  │  }                                                   │   │
│  │  ✅ Only metadata, no credentials or user data       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Endpoints                                        │   │
│  │  POST /query       - Process NL query                │   │
│  │  POST /metadata    - Receive metadata from client    │   │
│  │  POST /error-feedback - Handle SQL errors            │   │
│  │  DELETE /cache/:id - Clear cached metadata           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Request Flow Example

### 1. User Asks Question

```
User: "Show me all users who signed up last month"
```

**Client → Server:**
```http
POST /query HTTP/1.1
Content-Type: application/json

{
  "database_id": "my-postgres-db",
  "query": "Show me all users who signed up last month",
  "conversation_history": []
}
```

**Note:** No credentials sent! Just an ID and the query.

### 2. LLM Needs Metadata

**Server → Client:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "needs_metadata",
  "metadata_request": {
    "request_id": "my-postgres-db",
    "metadata_type": "tables",
    "params": {},
    "reason": "I need to know which tables exist in the database"
  }
}
```

### 3. User Approves & Client Fetches

**Client (User clicks "Approve"):**
```typescript
// This runs CLIENT-SIDE using Tauri
const tables = await invoke('get_database_tables', {
  databaseId: 'my-postgres-db'
});
// Uses stored credentials locally, credentials never leave client!
```

**Client → Server:**
```http
POST /metadata HTTP/1.1
Content-Type: application/json

{
  "request_id": "my-postgres-db",
  "metadata_type": "tables",
  "data": {
    "tables": ["users", "orders", "products", "reviews"]
  }
}
```

**Note:** Only metadata sent, no credentials!

### 4. LLM Needs Schema

**Server caches the tables, then:**

**Client → Server:** (User re-sends query)
```http
POST /query HTTP/1.1
```

**Server → Client:**
```http
{
  "status": "needs_metadata",
  "metadata_request": {
    "metadata_type": "schema",
    "params": {"table_name": "users"},
    "reason": "I need to see the structure of the users table"
  }
}
```

### 5. Client Fetches Schema

**Client:**
```typescript
const schema = await invoke('get_database_table_schema', {
  databaseId: 'my-postgres-db',
  tableName: 'users'
});
```

**Client → Server:**
```http
POST /metadata HTTP/1.1

{
  "metadata_type": "schema",
  "data": {
    "schema": {
      "table_name": "users",
      "columns": [
        {"name": "id", "type": "integer", "is_primary_key": true},
        {"name": "email", "type": "varchar(255)"},
        {"name": "created_at", "type": "timestamp"}
      ]
    }
  }
}
```

### 6. LLM Generates SQL

**Server has enough metadata now:**

**Server → Client:**
```http
{
  "status": "ready",
  "sql_response": {
    "sql": "SELECT * FROM users WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND created_at < DATE_TRUNC('month', CURRENT_DATE)",
    "explanation": "This query selects all users where the created_at timestamp is within the last month (from the start of last month to the start of this month).",
    "confidence": "high"
  }
}
```

### 7. Client Executes SQL

**Client:**
```typescript
// User clicks "Execute Query"
const results = await invoke('execute_sql_query', {
  databaseId: 'my-postgres-db',
  sql: generatedSQL
});
// Executed locally using stored credentials!
```

### 8. Display Results

Results displayed to user. No data ever went to the server!

## Security Properties

### ✅ What Server CAN Access
- Database IDs (arbitrary identifiers like "my-postgres-db")
- Natural language queries
- Metadata (table names, column names, types, relationships)
- Generated SQL queries
- Error messages from failed queries

### ❌ What Server CANNOT Access
- Database connection strings
- Usernames/passwords
- Database host addresses
- Actual data in the database
- Query results

## Comparison: Why NOT Use LangChain's SQLDatabase?

### LangChain SQLDatabase (Server-Side) - ❌ Wrong for Inspektor

```python
# Server needs connection string
from langchain_community.utilities import SQLDatabase

# ❌ Server connects to user's database
engine = create_engine("postgresql://user:password@host/db")
db = SQLDatabase(engine)

# ❌ Server executes queries
results = db.run("SELECT * FROM users")
```

**Problems:**
- Server needs credentials
- Server connects to user databases
- Security liability
- GDPR concerns

### Inspektor Approach (Client-Side) - ✅ Correct

```python
# Server never has connection string
# Client sends only metadata:

@app.post("/metadata")
async def submit_metadata(response: MetadataResponse):
    # ✅ Server only receives metadata
    metadata_cache.update(
        database_id=response.request_id,
        metadata_type=response.metadata_type,
        data=response.data  # Just table/column names, no data!
    )
```

**Benefits:**
- Zero-trust architecture
- Credentials never leave client
- GDPR-compliant
- User approval for metadata access

## When to Use Which Approach?

### Use Inspektor's Approach (Client-Side) When:
- ✅ Users have sensitive databases
- ✅ Compliance requirements (GDPR, HIPAA, SOC2)
- ✅ Zero-trust architecture required
- ✅ Desktop/local application
- ✅ Users want control over metadata access

### Use LangChain SQLDatabase (Server-Side) When:
- ✅ You control all databases
- ✅ Internal tool for your own company
- ✅ Web application with server-side DB
- ✅ No compliance restrictions
- ✅ Convenience over security

## Files Overview

### Correct Implementation ✅
- **`server/main.py`** - Server without DB access
- **`server/agent.py`** - LLM agent that requests metadata
- **`server/cache.py`** - Metadata-only cache
- **`client/src/services/llm.ts`** - Client service (no credentials sent)
- **`client/src/components/QueryInterface.tsx`** - With metadata approval
- **`client/src/components/MetadataApproval.tsx`** - User approval UI

### Wrong Implementation ❌ (Reference Only)
- **`server/main_improved.py`** - Server WITH DB access (WRONG!)
- **`server/agent_improved.py`** - Uses LangChain SQLDatabase (WRONG!)
- **`client/src/services/llm-improved.ts`** - Sends credentials (WRONG!)

## Future Enhancements

### Better Server-Side Cache Options

While keeping credentials client-side, you can improve metadata caching:

**Option 1: Redis**
```python
import redis
redis_client = redis.Redis()
redis_client.setex(f"{db_id}:tables", 3600, json.dumps(tables))
```

**Option 2: SQLite**
```python
conn = sqlite3.connect('metadata_cache.db')
# Store metadata with TTL
```

**Option 3: Vector Store**
```python
# For semantic search of table/column descriptions
vectorstore = FAISS.from_texts(table_descriptions)
```

But remember: **Only cache metadata, never credentials or data!**

## Conclusion

Inspektor's architecture is designed for **security-first** use cases where:
- User databases must remain private
- Credentials must never leave the client
- Users want transparency and control
- Compliance is important

This architecture sacrifices some convenience (manual metadata approval) for significantly better security properties. This is the right trade-off for a desktop database tool.
