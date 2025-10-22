"""
Inspektor FastAPI Server
Handles LLM-based natural language to SQL conversion with iterative metadata gathering.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv

from agent import SQLAgent
from cache import MetadataCache

# Load environment variables
load_dotenv()

app = FastAPI(title="Inspektor LLM Server", version="0.1.0")

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost"],  # Tauri's default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
metadata_cache = MetadataCache()
sql_agent = SQLAgent(
    ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    model_name=os.getenv("OLLAMA_MODEL", "mistral:7b")
)


# Request/Response Models
class QueryRequest(BaseModel):
    """User's natural language query"""
    database_id: str
    query: str
    conversation_history: Optional[List[Dict[str, str]]] = []


class MetadataResponse(BaseModel):
    """Response containing metadata from client"""
    request_id: str
    metadata_type: str  # "tables", "schema", "relationships"
    data: Dict[str, Any]


class MetadataRequest(BaseModel):
    """LLM's request for additional metadata"""
    request_id: str
    metadata_type: str
    params: Optional[Dict[str, Any]] = {}
    reason: str  # Explanation for the user


class SQLResponse(BaseModel):
    """Final SQL query response"""
    sql: str
    explanation: str
    confidence: str  # "high", "medium", "low"


class QueryResponse(BaseModel):
    """Response from the LLM"""
    status: str  # "needs_metadata", "ready", "error"
    metadata_request: Optional[MetadataRequest] = None
    sql_response: Optional[SQLResponse] = None
    error: Optional[str] = None


class ErrorFeedback(BaseModel):
    """SQL execution error feedback to LLM"""
    database_id: str
    sql: str
    error_message: str
    original_query: str


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "ollama_url": os.getenv("OLLAMA_BASE_URL")}


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a natural language query.
    Returns either a metadata request or a final SQL query.
    """
    try:
        # Get cached metadata for this database
        cached_metadata = metadata_cache.get(request.database_id)

        # Process the query with the agent
        result = await sql_agent.process_query(
            query=request.query,
            database_id=request.database_id,
            cached_metadata=cached_metadata,
            conversation_history=request.conversation_history
        )

        return result
    except Exception as e:
        return QueryResponse(
            status="error",
            error=f"Failed to process query: {str(e)}"
        )


@app.post("/metadata")
async def submit_metadata(response: MetadataResponse):
    """
    Receive metadata from the client and cache it.
    """
    try:
        metadata_cache.update(
            database_id=response.request_id,
            metadata_type=response.metadata_type,
            data=response.data
        )
        return {"status": "success", "message": "Metadata cached successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cache metadata: {str(e)}")


@app.post("/error-feedback", response_model=QueryResponse)
async def handle_error_feedback(feedback: ErrorFeedback):
    """
    Handle SQL execution errors and attempt to generate a corrected query.
    """
    try:
        cached_metadata = metadata_cache.get(feedback.database_id)

        result = await sql_agent.handle_error(
            original_query=feedback.original_query,
            failed_sql=feedback.sql,
            error_message=feedback.error_message,
            cached_metadata=cached_metadata
        )

        return result
    except Exception as e:
        return QueryResponse(
            status="error",
            error=f"Failed to process error feedback: {str(e)}"
        )


@app.delete("/cache/{database_id}")
async def clear_cache(database_id: str):
    """Clear cached metadata for a specific database"""
    metadata_cache.clear(database_id)
    return {"status": "success", "message": f"Cache cleared for database {database_id}"}


@app.get("/cache/{database_id}")
async def get_cached_metadata(database_id: str):
    """Retrieve cached metadata for a database"""
    cached = metadata_cache.get(database_id)
    if cached:
        return {"status": "success", "metadata": cached}
    return {"status": "empty", "metadata": {}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", 8000))
    )
