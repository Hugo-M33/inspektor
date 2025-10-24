"""
Database migration script to add new workspace features.
Run this once to update your existing database schema.
"""

import sqlite3
import os
from pathlib import Path

def migrate_database(db_path: str = "./inspektor.db"):
    """
    Migrate the database to add workspace support.

    Args:
        db_path: Path to the SQLite database file
    """
    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if workspace_id column exists in conversations table
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'workspace_id' not in columns:
            print("Adding workspace_id column to conversations table...")
            cursor.execute("""
                ALTER TABLE conversations
                ADD COLUMN workspace_id TEXT
            """)
            print("✓ Added workspace_id column")
        else:
            print("✓ workspace_id column already exists")

        # Check if workspaces table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='workspaces'
        """)

        if not cursor.fetchone():
            print("Creating workspaces table...")
            cursor.execute("""
                CREATE TABLE workspaces (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE INDEX idx_workspace_user ON workspaces(user_id)
            """)
            print("✓ Created workspaces table")
        else:
            print("✓ workspaces table already exists")

        # Check if workspace_connections table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='workspace_connections'
        """)

        if not cursor.fetchone():
            print("Creating workspace_connections table...")
            cursor.execute("""
                CREATE TABLE workspace_connections (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    encrypted_data TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                CREATE INDEX idx_workspace_conn_workspace ON workspace_connections(workspace_id)
            """)
            print("✓ Created workspace_connections table")
        else:
            print("✓ workspace_connections table already exists")

        # Add index for workspace_id in conversations if it doesn't exist
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='index' AND name='idx_conversations_workspace'
        """)

        if not cursor.fetchone():
            print("Creating index on conversations.workspace_id...")
            cursor.execute("""
                CREATE INDEX idx_conversations_workspace ON conversations(workspace_id)
            """)
            print("✓ Created index")
        else:
            print("✓ Index already exists")

        conn.commit()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    # Default database path
    db_path = os.getenv("DATABASE_URL", "sqlite:///./inspektor.db")

    # Extract file path from SQLite URL
    if db_path.startswith("sqlite:///"):
        db_path = db_path.replace("sqlite:///", "")

    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        print("Creating new database with updated schema...")
        # The database.py module will create tables automatically
        from database import init_database
        init_database()
        print("✅ New database created!")
    else:
        migrate_database(db_path)
