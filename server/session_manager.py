"""
Session and conversation management for Inspektor.
Handles persistent conversation history and metadata caching in the database.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from database import Conversation, Message, MetadataCache, User
import uuid
from datetime import datetime, timedelta
import logging
from logger_config import logger as plogger

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages user conversations and metadata caching with database persistence.
    """

    def __init__(self, metadata_ttl_hours: int = 24):
        """
        Initialize session manager.

        Args:
            metadata_ttl_hours: Time-to-live for cached metadata in hours
        """
        self.metadata_ttl_hours = metadata_ttl_hours

    # ============ Conversation Management ============

    def create_conversation(
        self,
        db: Session,
        user_id: str,
        database_id: str,
        title: Optional[str] = None,
    ) -> Conversation:
        """
        Create a new conversation.

        Args:
            db: Database session
            user_id: User's ID
            database_id: Client-side database connection ID
            title: Optional conversation title

        Returns:
            Created Conversation object
        """
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            database_id=database_id,
            title=title or f"Conversation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        logger.info(f"Created conversation {conversation.id} for user {user_id}")
        return conversation

    def get_conversation(
        self,
        db: Session,
        conversation_id: str,
        user_id: str,
    ) -> Optional[Conversation]:
        """
        Get a conversation by ID (ensures it belongs to the user).

        Args:
            db: Database session
            conversation_id: Conversation ID
            user_id: User's ID (for authorization)

        Returns:
            Conversation object or None if not found
        """
        return (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .first()
        )

    def list_conversations(
        self,
        db: Session,
        user_id: str,
        database_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Conversation]:
        """
        List user's conversations.

        Args:
            db: Database session
            user_id: User's ID
            database_id: Optional filter by database ID
            limit: Maximum number of conversations to return
            offset: Pagination offset

        Returns:
            List of Conversation objects
        """
        query = db.query(Conversation).filter(Conversation.user_id == user_id)

        if database_id:
            query = query.filter(Conversation.database_id == database_id)

        return (
            query.order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def delete_conversation(
        self,
        db: Session,
        conversation_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete a conversation (ensures it belongs to the user).

        Args:
            db: Database session
            conversation_id: Conversation ID
            user_id: User's ID (for authorization)

        Returns:
            True if deleted, False if not found
        """
        conversation = self.get_conversation(db, conversation_id, user_id)

        if not conversation:
            return False

        db.delete(conversation)
        db.commit()

        logger.info(f"Deleted conversation {conversation_id}")
        return True

    # ============ Message Management ============

    def add_message(
        self,
        db: Session,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        Add a message to a conversation.

        Args:
            db: Database session
            conversation_id: Conversation ID
            role: Message role ("user", "assistant", "system")
            content: Message content
            metadata: Optional metadata (e.g., SQL queries, metadata requests)

        Returns:
            Created Message object
        """
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            message_metadata=metadata,
        )

        db.add(message)

        # Update conversation's updated_at timestamp
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            conversation.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(message)

        return message

    def get_conversation_messages(
        self,
        db: Session,
        conversation_id: str,
        user_id: str,
    ) -> List[Message]:
        """
        Get all messages in a conversation.

        Args:
            db: Database session
            conversation_id: Conversation ID
            user_id: User's ID (for authorization)

        Returns:
            List of Message objects ordered by timestamp
        """
        # First verify the conversation belongs to the user
        conversation = self.get_conversation(db, conversation_id, user_id)
        if not conversation:
            return []

        return (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp)
            .all()
        )

    def get_conversation_history_for_llm(
        self,
        db: Session,
        conversation_id: str,
        user_id: str,
        max_messages: int = 20,
    ) -> List[Dict[str, str]]:
        """
        Get conversation history formatted for LLM input.
        Includes context about metadata requests and responses to prevent re-requesting.

        Args:
            db: Database session
            conversation_id: Conversation ID
            user_id: User's ID (for authorization)
            max_messages: Maximum number of recent messages to include

        Returns:
            List of message dicts with 'role' and 'content'
        """
        plogger.separator("SESSION MANAGER: Formatting Conversation History", ".", 100)
        messages = self.get_conversation_messages(db, conversation_id, user_id)

        # Take only the most recent messages
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
        plogger.info(f"Total messages in DB: {len(messages)}, Using recent: {len(recent_messages)}")

        formatted_messages = []
        for i, msg in enumerate(recent_messages):
            # Build the message content
            content = msg.content
            plogger.info(f"Processing message {i+1}: role={msg.role}")

            # If this is an assistant message with metadata request info, add context
            if msg.role == "assistant" and msg.message_metadata:
                if "metadata_request" in msg.message_metadata:
                    req = msg.message_metadata["metadata_request"]
                    content += f"\n[Requested metadata: {req.get('metadata_type', 'unknown')}]"
                    plogger.metadata_request(f"Found metadata request in history: {req.get('metadata_type')}", indent=1)

            # If this is a system message with metadata response, format it clearly
            elif msg.role == "system" and msg.message_metadata:
                if "metadata_type" in msg.message_metadata and "data" in msg.message_metadata:
                    import json
                    metadata_type = msg.message_metadata["metadata_type"]
                    data = msg.message_metadata["data"]

                    # Create a concise summary of the metadata received
                    if metadata_type == "tables":
                        if isinstance(data, dict) and "tables" in data:
                            tables = data["tables"]
                            content = f"Metadata received (tables): {', '.join(tables) if isinstance(tables, list) else tables}"
                        else:
                            content = f"Metadata received (tables): {json.dumps(data)}"
                    elif metadata_type == "schema":
                        if isinstance(data, dict):
                            tables_with_schemas = list(data.keys())
                            content = f"Metadata received (schema) for tables: {', '.join(tables_with_schemas)}"
                        else:
                            content = f"Metadata received (schema): {json.dumps(data)[:200]}"
                    elif metadata_type == "relationships":
                        content = f"Metadata received (relationships)"
                    else:
                        content = f"Metadata received ({metadata_type})"

                    plogger.success(f"Found metadata response in history: {metadata_type}", indent=1)

            formatted_messages.append({
                "role": msg.role,
                "content": content
            })
            plogger.conversation_message(msg.role, content[:300], indent=1, max_length=300)

        plogger.info(f"Formatted {len(formatted_messages)} messages for LLM")
        return formatted_messages

    # ============ Metadata Cache Management ============

    def cache_metadata(
        self,
        db: Session,
        user_id: str,
        database_id: str,
        metadata_type: str,
        data: Dict[str, Any],
    ) -> MetadataCache:
        """
        Cache metadata for a database.

        Args:
            db: Database session
            user_id: User's ID
            database_id: Client-side database connection ID
            metadata_type: Type of metadata ("tables", "schema", "relationships")
            data: Metadata to cache

        Returns:
            Created or updated MetadataCache object
        """
        # Check if metadata already exists
        existing = (
            db.query(MetadataCache)
            .filter(
                MetadataCache.user_id == user_id,
                MetadataCache.database_id == database_id,
                MetadataCache.metadata_type == metadata_type,
            )
            .first()
        )

        expires_at = datetime.utcnow() + timedelta(hours=self.metadata_ttl_hours)

        if existing:
            # Update existing metadata
            existing.data = data
            existing.updated_at = datetime.utcnow()
            existing.expires_at = expires_at
            db.commit()
            db.refresh(existing)
            logger.info(f"Updated metadata cache: {metadata_type} for {database_id}")
            return existing
        else:
            # Create new metadata
            metadata_cache = MetadataCache(
                id=str(uuid.uuid4()),
                user_id=user_id,
                database_id=database_id,
                metadata_type=metadata_type,
                data=data,
                expires_at=expires_at,
            )
            db.add(metadata_cache)
            db.commit()
            db.refresh(metadata_cache)
            logger.info(f"Created metadata cache: {metadata_type} for {database_id}")
            return metadata_cache

    def get_cached_metadata(
        self,
        db: Session,
        user_id: str,
        database_id: str,
    ) -> Dict[str, Any]:
        """
        Get all cached metadata for a database.

        Args:
            db: Database session
            user_id: User's ID
            database_id: Client-side database connection ID

        Returns:
            Dictionary with metadata organized by type
        """
        # Get all metadata for this database
        metadata_entries = (
            db.query(MetadataCache)
            .filter(
                MetadataCache.user_id == user_id,
                MetadataCache.database_id == database_id,
            )
            .all()
        )

        result = {}

        for entry in metadata_entries:
            # Check if expired
            if entry.expires_at and entry.expires_at < datetime.utcnow():
                # Delete expired metadata
                db.delete(entry)
                continue

            # Add to result
            result[entry.metadata_type] = entry.data

        db.commit()

        return result

    def clear_metadata_cache(
        self,
        db: Session,
        user_id: str,
        database_id: str,
    ) -> int:
        """
        Clear all cached metadata for a database.

        Args:
            db: Database session
            user_id: User's ID
            database_id: Client-side database connection ID

        Returns:
            Number of cache entries deleted
        """
        deleted = (
            db.query(MetadataCache)
            .filter(
                MetadataCache.user_id == user_id,
                MetadataCache.database_id == database_id,
            )
            .delete()
        )
        db.commit()

        logger.info(f"Cleared {deleted} metadata cache entries for {database_id}")
        return deleted

    def cleanup_expired_metadata(self, db: Session) -> int:
        """
        Clean up all expired metadata entries.

        Args:
            db: Database session

        Returns:
            Number of entries deleted
        """
        deleted = (
            db.query(MetadataCache)
            .filter(
                MetadataCache.expires_at < datetime.utcnow(),
                MetadataCache.expires_at.isnot(None),
            )
            .delete()
        )
        db.commit()

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} expired metadata entries")

        return deleted
