"""
Metadata caching system for database schemas, tables, and relationships.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json


class MetadataCache:
    """
    In-memory cache for database metadata.
    Stores tables, schemas, relationships per database connection.
    """

    def __init__(self, ttl_minutes: int = 60):
        """
        Initialize the cache.

        Args:
            ttl_minutes: Time-to-live for cached data in minutes
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, datetime] = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def get(self, database_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached metadata for a database.

        Args:
            database_id: Unique identifier for the database connection

        Returns:
            Cached metadata dict or None if expired/not found
        """
        if database_id not in self._cache:
            return None

        # Check if cache is expired
        if self._is_expired(database_id):
            self.clear(database_id)
            return None

        return self._cache[database_id]

    def update(self, database_id: str, metadata_type: str, data: Dict[str, Any]) -> None:
        """
        Update cached metadata for a database.

        Args:
            database_id: Unique identifier for the database connection
            metadata_type: Type of metadata ("tables", "schema", "relationships")
            data: Metadata to cache
        """
        if database_id not in self._cache:
            self._cache[database_id] = {}

        self._cache[database_id][metadata_type] = data
        self._timestamps[database_id] = datetime.now()

    def clear(self, database_id: str) -> None:
        """
        Clear all cached metadata for a database.

        Args:
            database_id: Unique identifier for the database connection
        """
        if database_id in self._cache:
            del self._cache[database_id]
        if database_id in self._timestamps:
            del self._timestamps[database_id]

    def clear_all(self) -> None:
        """Clear all cached metadata for all databases."""
        self._cache.clear()
        self._timestamps.clear()

    def _is_expired(self, database_id: str) -> bool:
        """
        Check if cached data is expired.

        Args:
            database_id: Unique identifier for the database connection

        Returns:
            True if expired, False otherwise
        """
        if database_id not in self._timestamps:
            return True

        age = datetime.now() - self._timestamps[database_id]
        return age > self.ttl

    def get_age(self, database_id: str) -> Optional[timedelta]:
        """
        Get the age of cached data.

        Args:
            database_id: Unique identifier for the database connection

        Returns:
            Age as timedelta or None if not cached
        """
        if database_id not in self._timestamps:
            return None

        return datetime.now() - self._timestamps[database_id]

    def has_metadata_type(self, database_id: str, metadata_type: str) -> bool:
        """
        Check if a specific type of metadata is cached.

        Args:
            database_id: Unique identifier for the database connection
            metadata_type: Type of metadata to check

        Returns:
            True if cached and not expired, False otherwise
        """
        cached = self.get(database_id)
        if not cached:
            return False

        return metadata_type in cached

    def to_dict(self) -> Dict[str, Any]:
        """Export cache to dict for serialization."""
        return {
            "cache": self._cache,
            "timestamps": {
                db_id: ts.isoformat()
                for db_id, ts in self._timestamps.items()
            }
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Import cache from dict."""
        self._cache = data.get("cache", {})
        self._timestamps = {
            db_id: datetime.fromisoformat(ts)
            for db_id, ts in data.get("timestamps", {}).items()
        }
