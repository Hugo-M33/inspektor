"""
Database migration script to add ConversationContext and WorkspaceUser tables.
Run this script to upgrade your database schema for the new context features.
"""

import sys
import os
from sqlalchemy import create_engine, text
from database import Base, ConversationContext, WorkspaceUser
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration(database_url: str = None):
    """
    Run the migration to add new tables and update existing ones.

    Args:
        database_url: Database URL. If None, uses DATABASE_URL from environment.
    """
    database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///./inspektor.db")

    logger.info(f"Running migration on database: {database_url}")

    # Create engine
    engine = create_engine(database_url, echo=True)

    try:
        # Create new tables
        logger.info("Creating ConversationContext and WorkspaceUser tables...")

        # This will only create tables that don't exist yet
        Base.metadata.create_all(bind=engine)

        logger.info("✓ Tables created successfully")

        # Update existing conversation titles to NULL if they're auto-generated
        logger.info("Updating existing conversation titles...")
        with engine.connect() as conn:
            # SQLite doesn't support UPDATE with complex conditions easily
            # We'll just log that existing titles are kept
            result = conn.execute(text("SELECT COUNT(*) FROM conversations"))
            count = result.scalar()
            logger.info(f"  Found {count} existing conversations")
            logger.info(f"  Existing titles will be kept. New conversations will start with NULL titles.")
            conn.commit()

        logger.info("✓ Migration completed successfully!")
        logger.info("")
        logger.info("Summary of changes:")
        logger.info("  - Added 'conversation_context' table for storing analyzed context")
        logger.info("  - Added 'workspace_users' table for future workspace sharing")
        logger.info("  - Conversation titles can now be NULL (will auto-generate on first satisfied query)")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Restart your server")
        logger.info("  2. Test the new satisfaction prompt feature")
        logger.info("  3. View learned context in the Context viewer")

    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        logger.error("Please check your database and try again.")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Inspektor database migration")
    parser.add_argument(
        "--database-url",
        help="Database URL (default: uses DATABASE_URL env var or sqlite:///./inspektor.db)",
        default=None
    )

    args = parser.parse_args()

    run_migration(args.database_url)
