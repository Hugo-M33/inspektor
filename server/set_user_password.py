"""
CLI tool to set/reset user passwords in Inspektor.
Useful for administrative tasks and password recovery.
"""

import sys
import os
import argparse
from getpass import getpass
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import User
from auth import hash_password
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def set_user_password(email: str, password: str, database_url: str = None):
    """
    Set or reset a user's password.

    Args:
        email: User's email address
        password: New password (will be hashed)
        database_url: Database URL. If None, uses DATABASE_URL from environment.

    Returns:
        True if successful, False otherwise
    """
    database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///./inspektor.db")

    # Create engine and session
    engine = create_engine(database_url, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Find user by email
        user = session.query(User).filter(User.email == email).first()

        if not user:
            logger.error(f"❌ User with email '{email}' not found")
            return False

        # Hash the new password
        hashed_password = hash_password(password)

        # Update user's password
        user.hashed_password = hashed_password
        session.commit()

        logger.info(f"✅ Password updated successfully for user: {email}")
        logger.info(f"   User ID: {user.id}")
        logger.info(f"   Created: {user.created_at}")
        return True

    except Exception as e:
        session.rollback()
        logger.error(f"❌ Failed to update password: {e}")
        return False
    finally:
        session.close()


def list_users(database_url: str = None):
    """
    List all users in the database.

    Args:
        database_url: Database URL. If None, uses DATABASE_URL from environment.
    """
    database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///./inspektor.db")

    engine = create_engine(database_url, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        users = session.query(User).all()

        if not users:
            logger.info("No users found in database")
            return

        logger.info(f"\nFound {len(users)} user(s):")
        logger.info("-" * 80)
        for user in users:
            logger.info(f"Email: {user.email}")
            logger.info(f"  ID: {user.id}")
            logger.info(f"  Created: {user.created_at}")
            logger.info("-" * 80)

    except Exception as e:
        logger.error(f"❌ Failed to list users: {e}")
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Set or reset user passwords in Inspektor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Set password interactively (secure - password not shown in command history)
  python set_user_password.py user@example.com

  # Set password directly (less secure - visible in command history)
  python set_user_password.py user@example.com --password newpassword123

  # List all users
  python set_user_password.py --list

  # Use custom database
  python set_user_password.py user@example.com --database-url postgresql://localhost/inspektor
        """
    )

    parser.add_argument(
        "email",
        nargs="?",
        help="User's email address"
    )
    parser.add_argument(
        "-p", "--password",
        help="New password (if not provided, will prompt securely)"
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List all users in database"
    )
    parser.add_argument(
        "--database-url",
        help="Database URL (default: uses DATABASE_URL env var or sqlite:///./inspektor.db)",
        default=None
    )

    args = parser.parse_args()

    # List users mode
    if args.list:
        list_users(args.database_url)
        return

    # Set password mode
    if not args.email:
        parser.error("email is required (unless using --list)")

    # Get password
    if args.password:
        password = args.password
        logger.warning("⚠️  Warning: Password provided via command line is less secure")
    else:
        # Prompt for password securely
        print(f"Setting password for: {args.email}")
        password = getpass("Enter new password: ")
        password_confirm = getpass("Confirm new password: ")

        if password != password_confirm:
            logger.error("❌ Passwords do not match")
            sys.exit(1)

        if len(password) < 6:
            logger.error("❌ Password must be at least 6 characters")
            sys.exit(1)

    # Set the password
    success = set_user_password(args.email, password, args.database_url)

    if success:
        print("\n✅ Password updated successfully!")
        print(f"You can now log in with: {args.email}")
        sys.exit(0)
    else:
        print("\n❌ Failed to update password")
        sys.exit(1)


if __name__ == "__main__":
    main()
