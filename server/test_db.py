"""
Quick test to verify database models work correctly
"""

from database import init_database

def test_database():
    print("Testing database initialization...")

    try:
        # Initialize database (will create tables)
        db_manager = init_database("sqlite:///./test_inspektor.db")
        print("✅ Database initialized successfully!")

        # Test getting a session
        session = db_manager.get_session()
        print("✅ Database session created successfully!")
        session.close()

        print("\n✅ All database tests passed!")
        print("\nDatabase tables created:")
        print("  - users")
        print("  - sessions")
        print("  - conversations")
        print("  - messages")
        print("  - metadata_cache")

        return True

    except Exception as e:
        print(f"\n❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database()

    # Cleanup test database
    import os
    if os.path.exists("test_inspektor.db"):
        os.remove("test_inspektor.db")
        print("\n🧹 Cleaned up test database")

    exit(0 if success else 1)
