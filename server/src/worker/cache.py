import redis
import logging
from typing import Set
from uuid import UUID
from sqlmodel import Session, select

from src.config import settings
from src.models import RegisteredEvent

logger = logging.getLogger("AnalyticsWorker.Cache")

class SchemaCache:
    """
    Manages caching of allowed event types for projects using Redis.
    """

    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.ttl = 300 # TTL in seconds (5 minutes)

    def _get_key(self, project_id: UUID) -> str:
        """
        Construct the Redis key for a project.
        """
        return f"project:{str(project_id)}:events"
    
    def get_allowed_events(self, session: Session, project_id: UUID) -> Set[str]:
        """
        Returns the set of allowed event names for a project.
        Checks Redis, if missing falls back to DB and populates cache.
        """
        key = self._get_key(project_id)

        try:
            cached_events = self.redis.smembers(key)
            if cached_events:
                return cached_events
        except redis.RedisError as e:
            logger.error(f"Redis read error: {e}. Falling back to DB.")

        logger.debug(f"Cache miss for {project_id}.")
        db_events = set(session.exec(select(RegisteredEvent.event_name).where(
            RegisteredEvent.project_id == project_id
        )))
        logger.info(f"event: {db_events}")

        try:
            if db_events:
                self.redis.sadd(key, *db_events)
                self.redis.expire(key, self.ttl)
        except redis.RedisError as e:
            logger.error(f"Redis write error: {e}")

        return db_events
    
    def invalidate(self, project_id: UUID):
        """Deletes the cache key for a project."""
        try:
            key = self._get_key(project_id)
            self.redis.delete(key)
            logger.info(f"Invalidated cache for project {project_id}")
        except redis.RedisError as e:
            logger.error(f"Failed to invalidate cache: {e}")