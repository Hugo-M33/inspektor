"""
Database models and connection setup for Inspektor.
Handles user authentication, conversations, and metadata caching.
"""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import os
from typing import Optional

# Base class for all models
Base = declarative_base()


class User(Base):
    """User account model"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)  # UUID
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    metadata_cache = relationship("MetadataCache", back_populates="user", cascade="all, delete-orphan")
    workspaces = relationship("Workspace", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """Authentication session model (JWT tokens)"""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")


class Conversation(Base):
    """Conversation/chat session model"""
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True)
    database_id = Column(String(255), nullable=False)  # Client-side database connection ID (legacy, kept for backwards compat)
    title = Column(String(500), nullable=True)  # Auto-generated or user-provided title
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="conversations")
    workspace = relationship("Workspace", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.timestamp")

    # Indexes for efficient queries
    __table_args__ = (
        Index("idx_conversations_user_updated", "user_id", "updated_at"),
        Index("idx_conversations_workspace", "workspace_id"),
    )


class Message(Base):
    """Individual message in a conversation"""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)  # UUID
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # Store metadata requests, SQL queries, etc.
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    # Indexes
    __table_args__ = (
        Index("idx_messages_conversation_timestamp", "conversation_id", "timestamp"),
    )


class MetadataCache(Base):
    """Persistent metadata cache for database schemas"""
    __tablename__ = "metadata_cache"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    database_id = Column(String(255), nullable=False)  # Client-side database connection ID
    metadata_type = Column(String(50), nullable=False)  # "tables", "schema", "relationships"
    data = Column(JSON, nullable=False)  # The actual metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration

    # Relationships
    user = relationship("User", back_populates="metadata_cache")

    # Indexes for efficient lookups
    __table_args__ = (
        Index("idx_metadata_user_db_type", "user_id", "database_id", "metadata_type"),
    )


class Workspace(Base):
    """User workspace model"""
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="workspaces")
    connections = relationship("WorkspaceConnection", back_populates="workspace", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="workspace")
    contexts = relationship("WorkspaceContext", back_populates="workspace", cascade="all, delete-orphan")
    workspace_users = relationship("WorkspaceUser", back_populates="workspace", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_workspace_user", "user_id"),
    )


class WorkspaceConnection(Base):
    """Encrypted database connection stored in a workspace"""
    __tablename__ = "workspace_connections"

    id = Column(String(36), primary_key=True)  # UUID
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    encrypted_data = Column(Text, nullable=False)  # Base64-encoded encrypted credentials
    nonce = Column(String(255), nullable=False)  # Base64-encoded nonce
    salt = Column(String(255), nullable=False)  # Base64-encoded salt for key derivation
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="connections")

    # Indexes
    __table_args__ = (
        Index("idx_workspace_conn_workspace", "workspace_id"),
    )


class WorkspaceContext(Base):
    """
    Stores accumulated context at workspace level.
    Context includes learned relationships, typecast requirements, and business rules.
    Shared across all conversations and users in the workspace.
    """
    __tablename__ = "workspace_context"

    id = Column(String(36), primary_key=True)  # UUID
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    context_data = Column(JSON, nullable=False)  # Structured context extracted by LLM
    is_editable = Column(Integer, default=1, nullable=False)  # SQLite uses 0/1 for boolean
    created_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    source_conversation_id = Column(String(36), nullable=True)  # Optional: track where context came from
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="contexts")
    created_by = relationship("User", foreign_keys=[created_by_user_id])

    # Indexes
    __table_args__ = (
        Index("idx_workspace_context_workspace", "workspace_id"),
    )


class WorkspaceUser(Base):
    """
    Many-to-many relationship for workspace sharing (future feature).
    Allows multiple users to collaborate on a workspace.
    """
    __tablename__ = "workspace_users"

    id = Column(String(36), primary_key=True)  # UUID
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "owner" or "member"
    invited_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    accepted_at = Column(DateTime, nullable=True)  # NULL if invitation pending

    # Relationships
    workspace = relationship("Workspace", back_populates="workspace_users")
    user = relationship("User")

    # Indexes
    __table_args__ = (
        Index("idx_workspace_users_workspace", "workspace_id"),
        Index("idx_workspace_users_user", "user_id"),
    )


# Database connection management
class DatabaseManager:
    """Manages database connections and sessions"""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            database_url: SQLAlchemy database URL. If None, uses DATABASE_URL from env.
        """
        self.database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///./inspektor.db")
        self.engine = create_engine(
            self.database_url,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            pool_pre_ping=True,  # Verify connections before using
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all tables if they don't exist"""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(bind=self.engine)

    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()


# Global database manager instance
db_manager: Optional[DatabaseManager] = None


def init_database(database_url: Optional[str] = None) -> DatabaseManager:
    """
    Initialize the global database manager.

    Args:
        database_url: SQLAlchemy database URL

    Returns:
        DatabaseManager instance
    """
    global db_manager
    db_manager = DatabaseManager(database_url)
    db_manager.create_tables()
    return db_manager


def get_db():
    """
    FastAPI dependency for database sessions.
    Yields a database session and closes it after use.
    """
    if db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()
