#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script for Inspektor

This script migrates data from SQLite to PostgreSQL while preserving all relationships.
It's safe to run multiple times (idempotent) and includes validation.

Usage:
    python migrate-sqlite-to-postgres.py

Environment variables:
    SQLITE_DB_PATH: Path to SQLite database (default: ./inspektor.db)
    POSTGRES_URL: PostgreSQL connection URL (default: from DATABASE_URL env var)
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, inspect, MetaData
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Add parent directory to path to import database models
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    Base, User, Session as UserSession, Conversation, Message,
    MetadataCache, Workspace, WorkspaceConnection, WorkspaceContext, WorkspaceUser
)

# Colors for output
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def print_colored(text, color=NC):
    print(f"{color}{text}{NC}")

def get_table_count(engine, table_name):
    """Get row count for a table"""
    with engine.connect() as conn:
        result = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        return result.scalar()

def migrate_data():
    """
    Migrate all data from SQLite to PostgreSQL
    """
    # Get database URLs
    sqlite_path = os.getenv('SQLITE_DB_PATH', './inspektor.db')
    postgres_url = os.getenv('POSTGRES_URL') or os.getenv('DATABASE_URL')

    if not postgres_url:
        print_colored("Error: POSTGRES_URL or DATABASE_URL environment variable not set", RED)
        print("Example: export POSTGRES_URL='postgresql://inspektor:password@localhost:5432/inspektor'")
        sys.exit(1)

    # Check if PostgreSQL URL is actually PostgreSQL
    if not postgres_url.startswith('postgresql://'):
        print_colored(f"Error: POSTGRES_URL does not appear to be a PostgreSQL URL: {postgres_url}", RED)
        sys.exit(1)

    sqlite_url = f'sqlite:///{sqlite_path}'

    print_colored("=" * 60, BLUE)
    print_colored("Inspektor: SQLite to PostgreSQL Migration", BLUE)
    print_colored("=" * 60, BLUE)
    print()
    print(f"Source (SQLite):      {sqlite_path}")
    print(f"Destination (PostgreSQL): {postgres_url.split('@')[1] if '@' in postgres_url else postgres_url}")
    print()

    # Check if SQLite database exists
    if not os.path.exists(sqlite_path):
        print_colored(f"Error: SQLite database not found: {sqlite_path}", RED)
        sys.exit(1)

    try:
        # Create engines
        print_colored("Connecting to databases...", YELLOW)
        sqlite_engine = create_engine(sqlite_url, echo=False)
        postgres_engine = create_engine(postgres_url, echo=False)

        # Test connections
        with sqlite_engine.connect() as conn:
            conn.execute("SELECT 1")
        print_colored("✓ Connected to SQLite", GREEN)

        with postgres_engine.connect() as conn:
            conn.execute("SELECT 1")
        print_colored("✓ Connected to PostgreSQL", GREEN)
        print()

        # Create tables in PostgreSQL if they don't exist
        print_colored("Creating PostgreSQL tables...", YELLOW)
        Base.metadata.create_all(postgres_engine)
        print_colored("✓ PostgreSQL tables ready", GREEN)
        print()

        # Create sessions
        SqliteSession = sessionmaker(bind=sqlite_engine)
        PostgresSession = sessionmaker(bind=postgres_engine)

        sqlite_session = SqliteSession()
        postgres_session = PostgresSession()

        # Define migration order (respecting foreign key dependencies)
        migrations = [
            ('users', User),
            ('sessions', UserSession),
            ('workspaces', Workspace),
            ('workspace_connections', WorkspaceConnection),
            ('workspace_context', WorkspaceContext),
            ('workspace_users', WorkspaceUser),
            ('conversations', Conversation),
            ('messages', Message),
            ('metadata_cache', MetadataCache),
        ]

        print_colored("Starting data migration...", YELLOW)
        print()

        stats = {}

        for table_name, model_class in migrations:
            try:
                # Count records in source
                source_count = sqlite_session.query(model_class).count()

                if source_count == 0:
                    print(f"  {table_name}: No data to migrate")
                    stats[table_name] = {'source': 0, 'migrated': 0, 'status': 'empty'}
                    continue

                print(f"  {table_name}: Migrating {source_count} records...", end=' ')

                # Fetch all records from SQLite
                records = sqlite_session.query(model_class).all()

                # Check if PostgreSQL already has data
                existing_count = postgres_session.query(model_class).count()
                if existing_count > 0:
                    print_colored(f"SKIPPED (already has {existing_count} records)", YELLOW)
                    stats[table_name] = {
                        'source': source_count,
                        'migrated': existing_count,
                        'status': 'skipped'
                    }
                    continue

                # Insert records into PostgreSQL
                migrated = 0
                for record in records:
                    # Create a dictionary of the record's attributes
                    record_dict = {c.name: getattr(record, c.name)
                                  for c in record.__table__.columns}

                    # Create new instance
                    new_record = model_class(**record_dict)
                    postgres_session.add(new_record)
                    migrated += 1

                # Commit this table's data
                postgres_session.commit()
                print_colored(f"✓ {migrated} records", GREEN)

                stats[table_name] = {
                    'source': source_count,
                    'migrated': migrated,
                    'status': 'success'
                }

            except Exception as e:
                print_colored(f"✗ Error", RED)
                print_colored(f"    {str(e)}", RED)
                postgres_session.rollback()
                stats[table_name] = {
                    'source': source_count if 'source_count' in locals() else 0,
                    'migrated': 0,
                    'status': 'error',
                    'error': str(e)
                }

        # Close sessions
        sqlite_session.close()
        postgres_session.close()

        # Print summary
        print()
        print_colored("=" * 60, BLUE)
        print_colored("Migration Summary", BLUE)
        print_colored("=" * 60, BLUE)
        print()

        for table_name, stat in stats.items():
            status_symbol = "✓" if stat['status'] == 'success' else "⚠" if stat['status'] == 'skipped' else "○" if stat['status'] == 'empty' else "✗"
            status_color = GREEN if stat['status'] == 'success' else YELLOW if stat['status'] in ['skipped', 'empty'] else RED

            print_colored(f"  {status_symbol} {table_name:25} {stat['source']:>6} → {stat['migrated']:>6}  ({stat['status']})", status_color)

            if 'error' in stat:
                print_colored(f"      Error: {stat['error']}", RED)

        print()

        # Verify migration
        print_colored("Verifying migration...", YELLOW)
        verification_passed = True

        for table_name, model_class in migrations:
            if stats[table_name]['status'] not in ['success', 'skipped', 'empty']:
                verification_passed = False
                continue

            source_count = stats[table_name]['source']
            dest_count = stats[table_name]['migrated']

            if source_count != dest_count and stats[table_name]['status'] not in ['skipped']:
                print_colored(f"  ✗ {table_name}: Mismatch! Source={source_count}, Dest={dest_count}", RED)
                verification_passed = False

        if verification_passed:
            print_colored("✓ Verification passed", GREEN)
        else:
            print_colored("⚠ Verification found issues", YELLOW)

        print()
        print_colored("=" * 60, BLUE)

        if verification_passed:
            print_colored("Migration Complete!", GREEN)
            print()
            print("Next steps:")
            print("1. Update DATABASE_URL to point to PostgreSQL")
            print("2. Restart the application")
            print("3. Test all features")
            print("4. Keep SQLite database as backup")
        else:
            print_colored("Migration completed with warnings", YELLOW)
            print()
            print("Please review the errors above and fix them.")

        print_colored("=" * 60, BLUE)

    except Exception as e:
        print_colored(f"\nFatal error during migration: {e}", RED)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    migrate_data()
