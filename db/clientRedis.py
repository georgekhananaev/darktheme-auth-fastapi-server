import redis.asyncio as aioredis
from typing import Optional
from modules.config import config
from modules.logger import log_info, log_error

class AsyncRedisClient:
    """
    Singleton class for managing the Redis client.
    Provides a shared instance of the Redis client across the application.
    """
    _instance = None

    @classmethod
    async def get_instance(cls):
        """
        Get or create the Redis client instance.
        
        Returns:
            Redis client instance or None if Redis is disabled
        """
        if cls._instance is None:
            cls._instance = await cls.create_redis_client()
        return cls._instance

    @staticmethod
    async def create_redis_client() -> Optional[aioredis.Redis]:
        """
        Create a new Redis client.
        
        Returns:
            Redis client instance or None if Redis is disabled
        """
        # Check if Redis is enabled
        if not config.is_redis_enabled():
            log_info("Redis is disabled in configuration. Skipping connection.")
            return None
        
        # Get Redis configuration
        redis_config = config.get_redis_config()
        hosts = redis_config.get('hosts', ['localhost', 'redis', '0.0.0.0'])
        port = redis_config.get('port', 6379)
        db = redis_config.get('db', 0)
        decode_responses = redis_config.get('decode_responses', True)
        
        # Try to connect to Redis using any of the provided hosts
        for host in hosts:
            try:
                redis_client = aioredis.StrictRedis(
                    host=host, 
                    port=port, 
                    db=db, 
                    decode_responses=decode_responses
                )
                if await redis_client.ping():
                    log_info(f"Successfully connected to Redis server at {host}")
                    return redis_client
            except aioredis.ConnectionError as e:
                log_error(f"Could not connect to Redis server at {host}: {e}.")
        
        # If we get here, we couldn't connect to any of the Redis servers
        if config.is_redis_enabled():
            raise Exception("Could not connect to any Redis server.")
        return None
        
    @staticmethod
    async def close():
        """Close the Redis client connection."""
        if AsyncRedisClient._instance:
            await AsyncRedisClient._instance.close()
            AsyncRedisClient._instance = None
            log_info("Redis connection closed.")