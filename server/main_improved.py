"""
⚠️ WARNING: DO NOT USE THIS FILE! ⚠️

This implementation breaks Inspektor's security model!

PROBLEMS:
- ❌ Server receives database credentials from client
- ❌ Server connects directly to user databases
- ❌ Credentials travel over the network
- ❌ Defeats client-only execution principle

USE main.py INSTEAD - the correct implementation where:
- ✅ Credentials never leave the client
- ✅ All DB queries execute client-side
- ✅ Server only handles LLM reasoning
- ✅ Metadata requested through approval workflow

This file kept for reference only.
"""

# DEPRECATED - DO NOT USE

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

from agent_improved import ImprovedSQLAgent

# Load environment variables
load_dotenv()

app = FastAPI(title="Inspektor LLM Server", version="0.2.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
sql_agent = ImprovedSQLAgent(
    ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    model_name=os.getenv("OLLAMA_MODEL", "mistral:7b")
)


# Request/Response Models
class DatabaseConnection(BaseModel):
    """Database connection details"""
    db_type: str  # "postgres", "mysql", "sqlite"
    host: Optional[str] = None
    port: Optional[int] = None
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    file_path: Optional[str] = None  # For SQLite
    schema: Optional[str] = None  # For PostgreSQL


class QueryRequest(BaseModel):
    """User's natural language query"""
    #database_id: str
    query: str
    #connection: DatabaseConnection  # Connection details sent with each request


class SQLResponse(BaseModel):
    """Final SQL query response"""
    sql: str
    explanation: str
    confidence: str


class QueryResponse(BaseModel):
    """Response from the LLM"""
    status: str  # "ready", "error"
    sql_response: Optional[SQLResponse] = None
    error: Optional[str] = None


class ErrorFeedback(BaseModel):
    """SQL execution error feedback"""
    database_id: str
    sql: str
    error_message: str
    original_query: str
    connection: DatabaseConnection


class SchemaRequest(BaseModel):
    """Request to get schema info"""
    database_id: str
    connection: DatabaseConnection


def build_connection_string(conn: DatabaseConnection) -> str:
    """
    Build SQLAlchemy connection string from connection details.

    Args:
        conn: Database connection details

    Returns:
        SQLAlchemy connection string
    """
    if conn.db_type == "postgres":
        return f"postgresql+psycopg2://{conn.username}:{conn.password}@{conn.host}:{conn.port or 5432}/{conn.database}"
    elif conn.db_type == "mysql":
        return f"mysql+pymysql://{conn.username}:{conn.password}@{conn.host}:{conn.port or 3306}/{conn.database}"
    elif conn.db_type == "sqlite":
        return f"sqlite:///{conn.file_path}"
    else:
        raise ValueError(f"Unsupported database type: {conn.db_type}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "ollama_url": os.getenv("OLLAMA_BASE_URL")}


@app.post("/query", response_model=QueryResponse)
async def process_query(request: Dict):
    """
    Process a natural language query using LangChain's SQL agent.

    The SQLDatabase wrapper automatically:
    - Introspects and caches the database schema
    - Provides tools to the agent for querying metadata
    - Executes read-only SQL queries

    No manual metadata requests needed - the agent handles it all!
    """
    print(request)
    try:
        # Build connection string
        conn_str = build_connection_string(request.connection)

        # Process query with agent
        # The agent automatically uses cached schema from SQLDatabase
        result = await sql_agent.process_query(
            query=request.query,
            database_id=request.database_id,
            connection_string=conn_str,
            schema=request.connection.schema
        )

        return result

    except Exception as e:
        print(e)
        return QueryResponse(
            status="error",
            error=f"Failed to process query: {str(e)}"
        )


@app.post("/error-feedback", response_model=QueryResponse)
async def handle_error_feedback(feedback: ErrorFeedback):
    """
    Handle SQL execution errors - agent will fix the query.
    """
    try:
        conn_str = build_connection_string(feedback.connection)

        result = await sql_agent.handle_error(
            original_query=feedback.original_query,
            failed_sql=feedback.sql,
            error_message=feedback.error_message,
            database_id=feedback.database_id,
            connection_string=conn_str,
            schema=feedback.connection.schema
        )

        return result

    except Exception as e:
        return QueryResponse(
            status="error",
            error=f"Failed to process error feedback: {str(e)}"
        )


@app.post("/schema-info")
async def get_schema_info(request: SchemaRequest):
    """
    Get cached schema information for a database.
    The schema is automatically cached by SQLDatabase wrapper.
    """
    try:
        # Ensure connection exists (this will cache schema if not already cached)
        conn_str = build_connection_string(request.connection)
        sql_agent._get_or_create_db_connection(
            request.database_id,
            conn_str,
            request.connection.schema
        )

        # Get schema info
        schema_info = sql_agent.get_schema_info(request.database_id)
        return {"status": "success", "schema": schema_info}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get schema: {str(e)}")


@app.delete("/cache/{database_id}")
async def clear_cache(database_id: str):
    """Clear cached schema and agent for a specific database"""
    sql_agent.clear_cache(database_id)
    return {"status": "success", "message": f"Cache cleared for database {database_id}"}


@app.delete("/cache")
async def clear_all_cache():
    """Clear all cached schemas and agents"""
    sql_agent.clear_cache()
    return {"status": "success", "message": "All caches cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", 8000))
    )
