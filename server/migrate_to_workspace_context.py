"""
Migration script to convert ConversationContext to WorkspaceContext.
Migrates from conversation-level context to workspace-level context with intelligent merging.
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def merge_context_data(contexts):
    """
    Merge multiple context data objects into a single workspace context.
    Uses the same logic as session_manager._merge_context_data but for batch merging.
    """
    merged = {
        "tables_used": [],
        "relationships": [],
        "column_typecast_hints": [],
        "business_context": [],
        "sql_patterns": []
    }

    # Collect all tables (deduplicated)
    tables_set = set()
    for ctx in contexts:
        tables_set.update(ctx.get("tables_used", []))
    merged["tables_used"] = sorted(list(tables_set))

    # Merge relationships (deduplicate by signature)
    rel_signatures = set()
    for ctx in contexts:
        for rel in ctx.get("relationships", []):
            if isinstance(rel, dict):
                sig = f"{rel.get('from_table')}.{rel.get('from_column')}->{rel.get('to_table')}.{rel.get('to_column')}"
                if sig not in rel_signatures:
                    rel_signatures.add(sig)
                    merged["relationships"].append(rel)

    # Merge typecast hints (deduplicate by table.column, keep latest)
    hint_map = {}
    for ctx in contexts:
        for hint in ctx.get("column_typecast_hints", []):
            if isinstance(hint, dict):
                key = f"{hint.get('table')}.{hint.get('column')}"
                hint_map[key] = hint
    merged["column_typecast_hints"] = list(hint_map.values())

    # Merge business context (deduplicate)
    biz_set = set()
    for ctx in contexts:
        biz_set.update(ctx.get("business_context", []))
    merged["business_context"] = sorted(list(biz_set))

    # Merge SQL patterns (deduplicate by pattern name, keep latest)
    pattern_map = {}
    for ctx in contexts:
        for pattern in ctx.get("sql_patterns", []):
            if isinstance(pattern, dict):
                key = pattern.get("pattern", "")
                if key:
                    pattern_map[key] = pattern
    merged["sql_patterns"] = list(pattern_map.values())

    return merged


def run_migration(database_url: str = None):
    """
    Run the migration from conversation_context to workspace_context.

    Args:
        database_url: Database URL. If None, uses DATABASE_URL from environment.
    """
    database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///./inspektor.db")

    logger.info(f"Running migration on database: {database_url}")
    logger.info("=" * 80)

    # Create engine and session
    engine = create_engine(database_url, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Step 1: Check if old table exists
        logger.info("Step 1: Checking for conversation_context table...")
        result = session.execute(text("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='conversation_context'
        """))
        old_table_exists = result.fetchone() is not None

        if not old_table_exists:
            logger.info("  ✓ No conversation_context table found - assuming fresh installation")
            logger.info("  Creating workspace_context table...")

            # Create new table
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS workspace_context (
                    id VARCHAR(36) PRIMARY KEY,
                    workspace_id VARCHAR(36) NOT NULL,
                    context_data JSON NOT NULL,
                    is_editable INTEGER DEFAULT 1 NOT NULL,
                    created_by_user_id VARCHAR(36),
                    source_conversation_id VARCHAR(36),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
                    FOREIGN KEY(created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """))

            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_workspace_context_workspace
                ON workspace_context(workspace_id)
            """))

            session.commit()
            logger.info("  ✓ workspace_context table created")
            logger.info("=" * 80)
            logger.info("Migration completed successfully! (fresh installation)")
            return

        logger.info("  ✓ Found conversation_context table - will migrate data")

        # Step 2: Get all existing conversation contexts
        logger.info("\nStep 2: Reading existing conversation contexts...")
        result = session.execute(text("""
            SELECT id, conversation_id, workspace_id, context_data,
                   created_by_user_id, created_at, updated_at
            FROM conversation_context
        """))
        old_contexts = result.fetchall()
        logger.info(f"  Found {len(old_contexts)} conversation contexts")

        if len(old_contexts) == 0:
            logger.info("  No data to migrate")
        else:
            # Step 3: Group contexts by workspace_id
            logger.info("\nStep 3: Grouping contexts by workspace...")

            # First, get workspace_id for each conversation
            workspace_contexts = defaultdict(list)
            context_metadata = {}

            for ctx in old_contexts:
                ctx_id, conv_id, ws_id, ctx_data_str, created_by, created_at, updated_at = ctx

                # If workspace_id is not set, get it from conversation
                if not ws_id:
                    result = session.execute(text("""
                        SELECT workspace_id FROM conversations WHERE id = :conv_id
                    """), {"conv_id": conv_id})
                    row = result.fetchone()
                    if row:
                        ws_id = row[0]

                if ws_id:
                    # Parse context data
                    try:
                        ctx_data = json.loads(ctx_data_str)
                        workspace_contexts[ws_id].append(ctx_data)

                        # Track metadata (use latest for each workspace)
                        if ws_id not in context_metadata or updated_at > context_metadata[ws_id]['updated_at']:
                            context_metadata[ws_id] = {
                                'created_by_user_id': created_by,
                                'source_conversation_id': conv_id,
                                'created_at': created_at,
                                'updated_at': updated_at
                            }
                    except json.JSONDecodeError:
                        logger.warning(f"  ! Could not parse context data for context {ctx_id}")
                        continue
                else:
                    logger.warning(f"  ! Could not find workspace for conversation {conv_id}")

            logger.info(f"  Grouped into {len(workspace_contexts)} workspaces")

            # Step 4: Create workspace_context table
            logger.info("\nStep 4: Creating workspace_context table...")
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS workspace_context (
                    id VARCHAR(36) PRIMARY KEY,
                    workspace_id VARCHAR(36) NOT NULL,
                    context_data JSON NOT NULL,
                    is_editable INTEGER DEFAULT 1 NOT NULL,
                    created_by_user_id VARCHAR(36),
                    source_conversation_id VARCHAR(36),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
                    FOREIGN KEY(created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """))

            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_workspace_context_workspace
                ON workspace_context(workspace_id)
            """))
            logger.info("  ✓ workspace_context table created")

            # Step 5: Merge and insert data
            logger.info("\nStep 5: Merging and inserting workspace contexts...")
            import uuid

            for ws_id, contexts in workspace_contexts.items():
                # Merge all contexts for this workspace
                merged_context = merge_context_data(contexts)
                metadata = context_metadata[ws_id]

                # Insert merged context
                session.execute(text("""
                    INSERT INTO workspace_context
                    (id, workspace_id, context_data, is_editable, created_by_user_id,
                     source_conversation_id, created_at, updated_at)
                    VALUES (:id, :workspace_id, :context_data, 1, :created_by,
                            :source_conv, :created_at, :updated_at)
                """), {
                    "id": str(uuid.uuid4()),
                    "workspace_id": ws_id,
                    "context_data": json.dumps(merged_context),
                    "created_by": metadata['created_by_user_id'],
                    "source_conv": metadata['source_conversation_id'],
                    "created_at": metadata['created_at'],
                    "updated_at": metadata['updated_at']
                })

                logger.info(f"  ✓ Merged {len(contexts)} contexts for workspace {ws_id[:8]}...")
                logger.info(f"    - Tables: {len(merged_context['tables_used'])}")
                logger.info(f"    - Relationships: {len(merged_context['relationships'])}")
                logger.info(f"    - Business rules: {len(merged_context['business_context'])}")

            session.commit()
            logger.info(f"  ✓ Inserted {len(workspace_contexts)} workspace contexts")

        # Step 6: Drop old table
        logger.info("\nStep 6: Dropping old conversation_context table...")
        session.execute(text("DROP TABLE IF EXISTS conversation_context"))
        session.commit()
        logger.info("  ✓ Dropped conversation_context table")

        logger.info("=" * 80)
        logger.info("✓ Migration completed successfully!")
        logger.info("")
        logger.info("Summary:")
        logger.info(f"  - Migrated {len(old_contexts)} conversation contexts")
        logger.info(f"  - Created {len(workspace_contexts)} workspace contexts")
        logger.info(f"  - Contexts are now shared across all conversations in each workspace")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Restart your server")
        logger.info("  2. Test querying - context will now be workspace-wide")
        logger.info("  3. New learnings will merge into existing workspace context")

    except Exception as e:
        session.rollback()
        logger.error(f"✗ Migration failed: {e}")
        logger.error("Database has been rolled back to previous state")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate from conversation_context to workspace_context")
    parser.add_argument(
        "--database-url",
        help="Database URL (default: uses DATABASE_URL env var or sqlite:///./inspektor.db)",
        default=None
    )

    args = parser.parse_args()

    run_migration(args.database_url)
