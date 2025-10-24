"""
Inspektor FastAPI Server with OpenAI and Authentication
Handles user authentication, LLM-based SQL generation, and conversation persistence.
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
import os
import logging
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Import our modules
from database import init_database, get_db, User, Workspace, WorkspaceConnection
from auth import (
    register_user,
    authenticate_user,
    create_access_token,
    create_session,
    validate_session,
    logout_user,
    UserExistsError,
    InvalidCredentialsError,
    TokenExpiredError,
    AuthError,
)
from agent_openai import SQLAgent
from session_manager import SessionManager
from llm_interface import LLMError
from logger_config import logger as plogger

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Inspektor API",
    version="2.0.0",
    description="Natural language to SQL with authentication and OpenAI"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_database()

# Initialize components
sql_agent = SQLAgent(
    api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
)
session_manager = SessionManager(
    metadata_ttl_hours=int(os.getenv("METADATA_TTL_HOURS", "24"))
)


# ============ Request/Response Models ============

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: str
    expires_in: int
    user: Dict[str, Any]

class QueryRequest(BaseModel):
    database_id: str
    query: str
    conversation_id: Optional[str] = None

class MetadataResponse(BaseModel):
    database_id: str
    metadata_type: str
    data: Dict[str, Any]

class MetadataRequest(BaseModel):
    metadata_type: str
    params: Optional[Dict[str, Any]] = {}
    reason: str

class SQLResponse(BaseModel):
    sql: str
    explanation: str
    confidence: str

class QueryResponse(BaseModel):
    status: str
    conversation_id: str
    metadata_request: Optional[MetadataRequest] = None
    sql_response: Optional[SQLResponse] = None
    message: Optional[str] = None
    error: Optional[str] = None

class ErrorFeedback(BaseModel):
    database_id: str
    conversation_id: str
    sql: str
    error_message: str
    original_query: str

class ConversationSummary(BaseModel):
    id: str
    database_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int

class ConversationDetail(BaseModel):
    id: str
    database_id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[Dict[str, Any]]

class WorkspaceCreate(BaseModel):
    name: str

class WorkspaceResponse(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str
    connection_count: int

class WorkspaceConnectionCreate(BaseModel):
    name: str
    encrypted_data: str
    nonce: str
    salt: str

class WorkspaceConnectionResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    encrypted_data: str
    nonce: str
    salt: str
    created_at: str
    updated_at: str


# ============ Authentication Helpers ============

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get current authenticated user from Authorization header.

    Args:
        authorization: Authorization header value ("Bearer <token>")
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization[7:]  # Remove "Bearer " prefix

    try:
        user = validate_session(db, token)
        return user
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ============ Health & Info Endpoints ============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "llm_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    }


# ============ Authentication Endpoints ============

@app.post("/auth/register", response_model=LoginResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Args:
        request: Registration details (email, password)
        db: Database session

    Returns:
        Login response with access token
    """
    try:
        # Register user
        user = register_user(db, request.email, request.password)

        # Create access token
        token_data = create_access_token(user.id, user.email)

        # Create session in database
        from datetime import datetime
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        create_session(db, user.id, token_data["access_token"], expires_at)

        logger.info(f"New user registered: {user.email}")

        return LoginResponse(
            **token_data,
            user={
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
            }
        )

    except UserExistsError:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.

    Args:
        request: Login credentials
        db: Database session

    Returns:
        Login response with access token
    """
    try:
        # Authenticate user
        user = authenticate_user(db, request.email, request.password)

        # Create access token
        token_data = create_access_token(user.id, user.email)

        # Create session in database
        from datetime import datetime
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        create_session(db, user.id, token_data["access_token"], expires_at)

        logger.info(f"User logged in: {user.email}")

        return LoginResponse(
            **token_data,
            user={
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at.isoformat(),
            }
        )

    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@app.post("/auth/logout")
async def logout(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
):
    """
    Logout current user (invalidate session).

    Args:
        authorization: Authorization header
        db: Database session
    """
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    logout_user(db, token)
    return {"status": "success", "message": "Logged out successfully"}


@app.get("/auth/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        User information
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at.isoformat(),
    }


# ============ Query Endpoints ============

@app.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Process a natural language query.

    Args:
        request: Query request with database_id, query, and optional conversation_id
        current_user: Authenticated user
        db: Database session

    Returns:
        Query response with metadata request or SQL
    """
    try:
        plogger.separator(f"NEW QUERY REQUEST", "=", 100)
        plogger.info(f"Database ID: {request.database_id}")
        plogger.info(f"Query: {request.query[:200]}")
        plogger.info(f"Conversation ID: {request.conversation_id or '(new conversation)'}")

        # Get or create conversation
        if request.conversation_id:
            conversation = session_manager.get_conversation(
                db, request.conversation_id, current_user.id
            )
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            conversation = session_manager.create_conversation(
                db, current_user.id, request.database_id
            )
            plogger.success(f"Created new conversation: {conversation.id}")

        # Get cached metadata
        cached_metadata = session_manager.get_cached_metadata(
            db, current_user.id, request.database_id
        )
        plogger.metadata_summary(cached_metadata, indent=0)

        # Get conversation history for LLM
        conversation_history = session_manager.get_conversation_history_for_llm(
            db, conversation.id, current_user.id
        )
        plogger.separator("CONVERSATION HISTORY FOR LLM", "-", 100)
        if conversation_history:
            for i, msg in enumerate(conversation_history):
                plogger.conversation_message(msg["role"], msg["content"], indent=0)
        else:
            plogger.info("(no conversation history yet)")

        # Add user message to conversation (only if not empty - empty means continuation after metadata)
        if request.query.strip():
            session_manager.add_message(
                db, conversation.id, "user", request.query
            )

        # Process query with agent
        plogger.separator("CALLING SQL AGENT", "-", 100)
        result = sql_agent.process_query(
            query=request.query,
            database_id=request.database_id,
            cached_metadata=cached_metadata,
            conversation_history=conversation_history,
        )

        # Log result
        plogger.separator("AGENT RESULT", "-", 100)
        plogger.info(f"Status: {result.get('status')}")
        if result.get('metadata_request'):
            plogger.metadata_request(f"Metadata Type: {result['metadata_request'].get('metadata_type')}")
            plogger.metadata_request(f"Reason: {result['metadata_request'].get('reason')}")
        elif result.get('sql_response'):
            plogger.success(f"Generated SQL query")
            plogger.info(f"SQL: {result['sql_response'].get('sql', '')[:200]}")

        # Add assistant response to conversation
        # Only save new messages, not duplicates from continuations
        if result["status"] == "ready" and result.get("sql_response"):
            session_manager.add_message(
                db,
                conversation.id,
                "assistant",
                result["sql_response"]["explanation"],
                metadata={"sql": result["sql_response"]["sql"]},
            )
        elif result["status"] == "needs_metadata" and result.get("metadata_request") and request.query.strip():
            # Only save metadata request if this is a new query, not a continuation
            session_manager.add_message(
                db,
                conversation.id,
                "assistant",
                result["metadata_request"]["reason"],
                metadata={"metadata_request": result["metadata_request"]},
            )

        # Add conversation_id to response
        result["conversation_id"] = conversation.id

        return QueryResponse(**result)

    except LLMError as e:
        logger.error(f"LLM error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")


@app.post("/metadata")
async def submit_metadata(
    response: MetadataResponse,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Receive and cache metadata from the client.

    Args:
        response: Metadata from client
        current_user: Authenticated user
        db: Database session
    """
    try:
        plogger.separator(f"METADATA SUBMISSION", "=", 100)
        plogger.info(f"Database ID: {response.database_id}")
        plogger.info(f"Metadata Type: {response.metadata_type}")
        plogger.json_data(response.data, "Metadata Data", max_length=800)

        # Cache the metadata
        session_manager.cache_metadata(
            db,
            current_user.id,
            response.database_id,
            response.metadata_type,
            response.data,
        )
        plogger.success("Metadata cached successfully")

        # Find the most recent conversation for this database to add metadata to history
        # This helps LLM track what metadata it has already received
        conversations = session_manager.list_conversations(
            db, current_user.id, database_id=response.database_id, limit=1
        )

        if conversations:
            # Add a system message indicating metadata was provided
            import json
            metadata_summary = json.dumps(response.data, indent=2)[:500]  # Truncate if too long
            session_manager.add_message(
                db,
                conversations[0].id,
                "system",
                f"Metadata provided: {response.metadata_type}",
                metadata={
                    "metadata_type": response.metadata_type,
                    "data": response.data
                }
            )
            plogger.success(f"Added metadata submission to conversation {conversations[0].id}")
            logger.info(f"Added metadata submission to conversation {conversations[0].id}")
        else:
            plogger.warning("No conversation found to add metadata to")

        return {"status": "success", "message": "Metadata cached successfully"}
    except Exception as e:
        logger.error(f"Metadata submission error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cache metadata: {str(e)}")


@app.post("/error-feedback", response_model=QueryResponse)
async def handle_error_feedback(
    feedback: ErrorFeedback,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Handle SQL execution errors and generate corrected queries.

    Args:
        feedback: Error feedback from client
        current_user: Authenticated user
        db: Database session
    """
    try:
        plogger.separator("ERROR FEEDBACK - SQL EXECUTION FAILED", "=", 100)
        plogger.error(f"Database ID: {feedback.database_id}")
        plogger.error(f"Conversation ID: {feedback.conversation_id}")
        plogger.error(f"Failed SQL: {feedback.sql[:300]}")
        plogger.error(f"Error Message: {feedback.error_message[:300]}")
        plogger.info(f"Original Query: {feedback.original_query[:200]}")

        # Get cached metadata
        cached_metadata = session_manager.get_cached_metadata(
            db, current_user.id, feedback.database_id
        )
        plogger.metadata_summary(cached_metadata, indent=0)

        # Handle error with agent
        plogger.separator("CALLING AGENT TO FIX ERROR", "-", 100)
        result = sql_agent.handle_error(
            original_query=feedback.original_query,
            failed_sql=feedback.sql,
            error_message=feedback.error_message,
            cached_metadata=cached_metadata,
        )

        plogger.separator("ERROR HANDLING RESULT", "-", 100)
        plogger.info(f"Status: {result.get('status')}")
        if result.get('sql_response'):
            plogger.success("Generated corrected SQL")
            plogger.info(f"Corrected SQL: {result['sql_response'].get('sql', '')[:300]}")
        elif result.get('metadata_request'):
            plogger.warning(f"Needs more metadata: {result['metadata_request'].get('metadata_type')}")

        # Add error context to conversation
        conversation = session_manager.get_conversation(
            db, feedback.conversation_id, current_user.id
        )
        if conversation:
            session_manager.add_message(
                db,
                conversation.id,
                "system",
                f"SQL Error: {feedback.error_message}",
                metadata={"failed_sql": feedback.sql},
            )
            plogger.success("Added error to conversation history")

            if result["status"] == "ready" and result.get("sql_response"):
                session_manager.add_message(
                    db,
                    conversation.id,
                    "assistant",
                    result["sql_response"]["explanation"],
                    metadata={"sql": result["sql_response"]["sql"], "is_retry": True},
                )
                plogger.success("Added corrected SQL to conversation history")

        result["conversation_id"] = feedback.conversation_id
        return QueryResponse(**result)

    except Exception as e:
        logger.error(f"Error feedback handling error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to handle error: {str(e)}")


# ============ Conversation Management Endpoints ============

@app.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    database_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List user's conversations.

    Args:
        database_id: Optional filter by database
        limit: Maximum number of results
        offset: Pagination offset
        current_user: Authenticated user
        db: Database session
    """
    conversations = session_manager.list_conversations(
        db, current_user.id, database_id, limit, offset
    )

    return [
        ConversationSummary(
            id=conv.id,
            database_id=conv.database_id,
            title=conv.title,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat(),
            message_count=len(conv.messages),
        )
        for conv in conversations
    ]


@app.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed conversation with all messages.

    Args:
        conversation_id: Conversation ID
        current_user: Authenticated user
        db: Database session
    """
    conversation = session_manager.get_conversation(db, conversation_id, current_user.id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = session_manager.get_conversation_messages(db, conversation_id, current_user.id)

    return ConversationDetail(
        id=conversation.id,
        database_id=conversation.database_id,
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        messages=[
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "metadata": msg.message_metadata,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in messages
        ],
    )


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a conversation.

    Args:
        conversation_id: Conversation ID
        current_user: Authenticated user
        db: Database session
    """
    success = session_manager.delete_conversation(db, conversation_id, current_user.id)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "success", "message": "Conversation deleted"}


class MessageRequest(BaseModel):
    message: str
    database_id: str


@app.post("/conversations/{conversation_id}/message", response_model=QueryResponse)
async def send_message_to_conversation(
    conversation_id: str,
    request: MessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a follow-up message to an existing conversation.
    This allows users to provide additional context or refinements to the SQL query.

    Args:
        conversation_id: Conversation ID
        request: Message content and database_id
        current_user: Authenticated user
        db: Database session

    Returns:
        Query response with metadata request or SQL
    """
    try:
        plogger.separator(f"FOLLOW-UP MESSAGE TO CONVERSATION", "=", 100)
        plogger.info(f"Conversation ID: {conversation_id}")
        plogger.info(f"Database ID: {request.database_id}")
        plogger.info(f"Message: {request.message[:200]}")

        # Get conversation (ensures it belongs to user)
        conversation = session_manager.get_conversation(
            db, conversation_id, current_user.id
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Get cached metadata
        cached_metadata = session_manager.get_cached_metadata(
            db, current_user.id, request.database_id
        )
        plogger.metadata_summary(cached_metadata, indent=0)

        # Get conversation history for LLM
        conversation_history = session_manager.get_conversation_history_for_llm(
            db, conversation.id, current_user.id
        )
        plogger.separator("CONVERSATION HISTORY FOR LLM", "-", 100)
        if conversation_history:
            for i, msg in enumerate(conversation_history):
                plogger.conversation_message(msg["role"], msg["content"], indent=0)
        else:
            plogger.info("(no conversation history yet)")

        # Add user message to conversation
        session_manager.add_message(
            db, conversation.id, "user", request.message
        )

        # Process message with agent
        plogger.separator("CALLING SQL AGENT", "-", 100)
        result = sql_agent.process_query(
            query=request.message,
            database_id=request.database_id,
            cached_metadata=cached_metadata,
            conversation_history=conversation_history,
        )

        # Log result
        plogger.separator("AGENT RESULT", "-", 100)
        plogger.info(f"Status: {result.get('status')}")
        if result.get('metadata_request'):
            plogger.metadata_request(f"Metadata Type: {result['metadata_request'].get('metadata_type')}")
            plogger.metadata_request(f"Reason: {result['metadata_request'].get('reason')}")
        elif result.get('sql_response'):
            plogger.success(f"Generated SQL query")
            plogger.info(f"SQL: {result['sql_response'].get('sql', '')[:200]}")

        # Add assistant response to conversation
        if result["status"] == "ready" and result.get("sql_response"):
            session_manager.add_message(
                db,
                conversation.id,
                "assistant",
                result["sql_response"]["explanation"],
                metadata={"sql": result["sql_response"]["sql"]},
            )
        elif result["status"] == "needs_metadata" and result.get("metadata_request"):
            session_manager.add_message(
                db,
                conversation.id,
                "assistant",
                result["metadata_request"]["reason"],
                metadata={"metadata_request": result["metadata_request"]},
            )

        # Add conversation_id to response
        result["conversation_id"] = conversation.id

        return QueryResponse(**result)

    except LLMError as e:
        logger.error(f"LLM error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")
    except Exception as e:
        logger.error(f"Message processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")


# ============ Workspace Management Endpoints ============

@app.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(
    request: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new workspace.

    Args:
        request: Workspace creation request
        current_user: Authenticated user
        db: Database session

    Returns:
        Created workspace
    """
    import uuid

    workspace = Workspace(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=request.name,
    )

    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    logger.info(f"Created workspace {workspace.id} for user {current_user.id}")

    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        created_at=workspace.created_at.isoformat(),
        updated_at=workspace.updated_at.isoformat(),
        connection_count=0,
    )


@app.get("/workspaces", response_model=List[WorkspaceResponse])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List user's workspaces.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        List of workspaces
    """
    workspaces = db.query(Workspace).filter(Workspace.user_id == current_user.id).all()

    return [
        WorkspaceResponse(
            id=ws.id,
            name=ws.name,
            created_at=ws.created_at.isoformat(),
            updated_at=ws.updated_at.isoformat(),
            connection_count=len(ws.connections),
        )
        for ws in workspaces
    ]


@app.delete("/workspaces/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a workspace.

    Args:
        workspace_id: Workspace ID
        current_user: Authenticated user
        db: Database session
    """
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == current_user.id,
    ).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    db.delete(workspace)
    db.commit()

    logger.info(f"Deleted workspace {workspace_id}")

    return {"status": "success", "message": "Workspace deleted"}


@app.post("/workspaces/{workspace_id}/connections", response_model=WorkspaceConnectionResponse)
async def add_workspace_connection(
    workspace_id: str,
    request: WorkspaceConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add an encrypted connection to a workspace.

    Args:
        workspace_id: Workspace ID
        request: Connection creation request with encrypted data
        current_user: Authenticated user
        db: Database session

    Returns:
        Created connection
    """
    import uuid

    # Verify workspace belongs to user
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == current_user.id,
    ).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    connection = WorkspaceConnection(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        name=request.name,
        encrypted_data=request.encrypted_data,
        nonce=request.nonce,
        salt=request.salt,
    )

    db.add(connection)
    db.commit()
    db.refresh(connection)

    logger.info(f"Added connection {connection.id} to workspace {workspace_id}")

    return WorkspaceConnectionResponse(
        id=connection.id,
        workspace_id=connection.workspace_id,
        name=connection.name,
        encrypted_data=connection.encrypted_data,
        nonce=connection.nonce,
        salt=connection.salt,
        created_at=connection.created_at.isoformat(),
        updated_at=connection.updated_at.isoformat(),
    )


@app.get("/workspaces/{workspace_id}/connections", response_model=List[WorkspaceConnectionResponse])
async def list_workspace_connections(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all connections in a workspace.

    Args:
        workspace_id: Workspace ID
        current_user: Authenticated user
        db: Database session

    Returns:
        List of encrypted connections
    """
    # Verify workspace belongs to user
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == current_user.id,
    ).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    connections = db.query(WorkspaceConnection).filter(
        WorkspaceConnection.workspace_id == workspace_id
    ).all()

    return [
        WorkspaceConnectionResponse(
            id=conn.id,
            workspace_id=conn.workspace_id,
            name=conn.name,
            encrypted_data=conn.encrypted_data,
            nonce=conn.nonce,
            salt=conn.salt,
            created_at=conn.created_at.isoformat(),
            updated_at=conn.updated_at.isoformat(),
        )
        for conn in connections
    ]


@app.delete("/workspaces/{workspace_id}/connections/{connection_id}")
async def delete_workspace_connection(
    workspace_id: str,
    connection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a connection from a workspace.

    Args:
        workspace_id: Workspace ID
        connection_id: Connection ID
        current_user: Authenticated user
        db: Database session
    """
    # Verify workspace belongs to user
    workspace = db.query(Workspace).filter(
        Workspace.id == workspace_id,
        Workspace.user_id == current_user.id,
    ).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    connection = db.query(WorkspaceConnection).filter(
        WorkspaceConnection.id == connection_id,
        WorkspaceConnection.workspace_id == workspace_id,
    ).first()

    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    db.delete(connection)
    db.commit()

    logger.info(f"Deleted connection {connection_id} from workspace {workspace_id}")

    return {"status": "success", "message": "Connection deleted"}


@app.delete("/cache/{database_id}")
async def clear_cache(
    database_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear cached metadata for a database"""
    deleted = session_manager.clear_metadata_cache(db, current_user.id, database_id)
    return {
        "status": "success",
        "message": f"Cleared {deleted} metadata entries for database {database_id}",
    }


# ============ Admin/Utility Endpoints ============

@app.get("/stats")
async def get_stats(current_user: User = Depends(get_current_user)):
    """Get LLM usage statistics"""
    return {
        "token_usage": sql_agent.get_token_usage(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", 8000)),
    )
