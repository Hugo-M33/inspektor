"""
Fix conversations with NULL workspace_id.
Associates orphaned conversations with a user's default workspace.
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_conversation_workspace_ids(database_url: str = None):
    """
    Fix conversations that have NULL workspace_id.

    For each conversation without a workspace:
    1. Find the user who owns the conversation
    2. Get or create a default workspace for that user
    3. Associate the conversation with that workspace

    Args:
        database_url: Database URL. If None, uses DATABASE_URL from environment.
    """
    database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///./inspektor.db")

    logger.info(f"Fixing conversation workspace_ids in: {database_url}")
    logger.info("=" * 80)

    engine = create_engine(database_url, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Find conversations without workspace_id
        result = session.execute(text("""
            SELECT id, user_id, database_id, title, created_at
            FROM conversations
            WHERE workspace_id IS NULL
        """))
        orphaned_conversations = result.fetchall()

        if not orphaned_conversations:
            logger.info("✓ All conversations already have workspace_id!")
            logger.info("No fixes needed.")
            return

        logger.info(f"Found {len(orphaned_conversations)} conversations without workspace_id")
        logger.info("")

        # Group by user_id
        user_conversations = {}
        for conv in orphaned_conversations:
            conv_id, user_id, db_id, title, created_at = conv
            if user_id not in user_conversations:
                user_conversations[user_id] = []
            user_conversations[user_id].append((conv_id, db_id, title, created_at))

        # Fix each user's conversations
        for user_id, conversations in user_conversations.items():
            logger.info(f"Processing user {user_id[:8]}... ({len(conversations)} conversations)")

            # Check if user has any workspaces
            result = session.execute(text("""
                SELECT id, name FROM workspaces
                WHERE user_id = :user_id
                ORDER BY created_at ASC
                LIMIT 1
            """), {"user_id": user_id})
            workspace = result.fetchone()

            if workspace:
                workspace_id, workspace_name = workspace
                logger.info(f"  Using existing workspace: {workspace_name}")
            else:
                # Create a default workspace for this user
                workspace_id = str(uuid.uuid4())
                workspace_name = "Default Workspace"

                session.execute(text("""
                    INSERT INTO workspaces (id, user_id, name, created_at, updated_at)
                    VALUES (:id, :user_id, :name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """), {
                    "id": workspace_id,
                    "user_id": user_id,
                    "name": workspace_name
                })
                logger.info(f"  Created new workspace: {workspace_name}")

            # Update all conversations for this user
            for conv_id, db_id, title, created_at in conversations:
                session.execute(text("""
                    UPDATE conversations
                    SET workspace_id = :workspace_id
                    WHERE id = :conv_id
                """), {
                    "workspace_id": workspace_id,
                    "conv_id": conv_id
                })

                title_display = title if title else "(Untitled)"
                logger.info(f"    ✓ Fixed: {title_display[:50]}")

            session.commit()
            logger.info("")

        logger.info("=" * 80)
        logger.info(f"✓ Successfully fixed {len(orphaned_conversations)} conversations!")
        logger.info("")
        logger.info("Summary:")
        logger.info(f"  - Fixed conversations for {len(user_conversations)} user(s)")
        logger.info(f"  - All conversations now have workspace_id")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Restart your server")
        logger.info("  2. Context will now be stored at workspace level")

    except Exception as e:
        session.rollback()
        logger.error(f"✗ Failed to fix conversations: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix conversations with NULL workspace_id")
    parser.add_argument(
        "--database-url",
        help="Database URL (default: uses DATABASE_URL env var or sqlite:///./inspektor.db)",
        default=None
    )

    args = parser.parse_args()

    fix_conversation_workspace_ids(args.database_url)
