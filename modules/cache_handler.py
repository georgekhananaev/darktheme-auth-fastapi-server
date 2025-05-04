import json
from typing import Optional, Dict, Any, Union, Tuple
from datetime import datetime
import httpx
from modules.logger import log_warning, log_error, log_info
from modules.config import config

# Check if Redis is enabled
REDIS_ENABLED = config.is_redis_enabled()

# Conditional import for Redis
if REDIS_ENABLED:
    from redis.asyncio import Redis
    from db.clientRedis import AsyncRedisClient


# Define fallback data in case external API is down
def generate_fallback_data():
    """Generate a fallback response for when APIs are unavailable"""
    now = datetime.now()
    return {
        "datetime": now.isoformat(),
        "unixtime": int(now.timestamp()),
        "utc_datetime": datetime.utcnow().isoformat(),
        "utc_offset": "0",
        "timezone": "UTC",
        "client_ip": "127.0.0.1",
        "day_of_week": now.strftime("%A"),
        "day_of_year": now.timetuple().tm_yday,
        "week_number": now.isocalendar()[1],
        "fallback": True
    }


class CacheHandler:
    """
    Handles caching operations with Redis, with graceful fallbacks when Redis is disabled
    or unavailable. Provides methods for getting, setting, and checking cache data.
    """

    @staticmethod
    async def get_redis_client() -> Optional[Any]:
        """
        Returns the Redis client if Redis is enabled, or None if disabled.
        This is a dependency that should be used by FastAPI endpoints.
        """
        if REDIS_ENABLED:
            try:
                return await AsyncRedisClient.get_instance()
            except Exception:
                return None
        return None

    @staticmethod
    async def get_cache(redis, key: str) -> Tuple[bool, Any, int]:
        """
        Gets a value from the cache if available.
        
        Args:
            redis: The Redis client
            key: The cache key to retrieve
            
        Returns:
            Tuple[bool, Any, int]: (hit, value, ttl)
                - hit: True if cache hit, False if miss
                - value: The cached value if hit, None if miss
                - ttl: Time to live in seconds, 0 if miss
        """
        if not REDIS_ENABLED or redis is None:
            return False, None, 0
            
        try:
            cached_data = await redis.get(key)
            if cached_data:
                ttl = await redis.ttl(key)
                try:
                    return True, json.loads(cached_data), ttl
                except json.JSONDecodeError:
                    # If not JSON, return as-is (string)
                    return True, cached_data, ttl
        except Exception:
            pass
            
        return False, None, 0

    @staticmethod
    async def set_cache(redis, key: str, value: Any, expire_seconds: int = 300) -> bool:
        """
        Sets a value in the cache.
        
        Args:
            redis: The Redis client
            key: The cache key to set
            value: The value to cache (will be JSON serialized)
            expire_seconds: Time in seconds until the cache expires
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not REDIS_ENABLED or redis is None:
            return False
            
        try:
            if not isinstance(value, str):
                serialized_value = json.dumps(value)
            else:
                serialized_value = value
                
            await redis.set(key, serialized_value, ex=expire_seconds)
            return True
        except Exception:
            return False

    @staticmethod
    async def delete_cache(redis, keys: Union[str, list]) -> bool:
        """
        Deletes one or more keys from the cache.
        
        Args:
            redis: The Redis client
            keys: A single key or list of keys to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not REDIS_ENABLED or redis is None:
            return False
            
        try:
            if isinstance(keys, str):
                await redis.delete(keys)
            else:
                await redis.delete(*keys)
            return True
        except Exception:
            return False

    @staticmethod
    async def check_health(redis) -> Dict[str, Any]:
        """
        Checks Redis health and returns status details.
        
        Args:
            redis: The Redis client
            
        Returns:
            Dict: A dictionary with Redis health information
        """
        if not REDIS_ENABLED:
            return {
                "status": "disabled",
                "enabled": False,
                "message": "Redis is disabled in configuration"
            }

        if redis is None:
            return {
                "status": "error",
                "enabled": True,
                "message": "Redis is enabled but client initialization failed"
            }

        try:
            # Check if Redis is responding
            ping_result = await redis.ping()
            if ping_result:
                # Get Redis info
                info = await redis.info()
                return {
                    "status": "healthy",
                    "enabled": True,
                    "message": "Redis is connected and responding",
                    "redis_version": info.get("redis_version", "unknown"),
                    "connected_clients": info.get("connected_clients", "unknown"),
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                    "uptime_in_days": info.get("uptime_in_days", "unknown")
                }
            else:
                return {
                    "status": "error",
                    "enabled": True,
                    "message": "Redis ping failed"
                }
        except Exception as e:
            return {
                "status": "error",
                "enabled": True,
                "message": f"Redis health check failed: {str(e)}"
            }

    @staticmethod
    async def cache_result(cache_key: str, result: Any, expire_seconds: int, redis) -> Dict[str, Any]:
        """
        Caches a result in Redis and returns cache details.

        This function stores the given result in the Redis cache under the specified
        cache_key with an expiration time of expire_seconds. It then retrieves the
        time-to-live (TTL) for the cache key and returns the data along with the source
        information and TTL.

        Args:
            cache_key (str): The key under which the result will be stored in Redis.
            result (Any): The result data to be cached.
            expire_seconds (int): The time in seconds after which the cache entry will expire.
            redis: The Redis client instance to interact with the cache.

        Returns:
            dict: A dictionary containing the cached data, the source ("cache"), and the TTL.
        """
        if not REDIS_ENABLED or redis is None:
            return {
                "data": result,
                "source": "no-cache",
                "time_left": 0
            }
            
        try:
            await CacheHandler.set_cache(redis, cache_key, result, expire_seconds)
            _, _, ttl = await CacheHandler.get_cache(redis, cache_key)
            return {
                "data": result,
                "source": "cache",
                "time_left": ttl
            }
        except Exception as e:
            log_error(f"Error caching result: {e}")
            return {
                "data": result,
                "source": "api-fallback",
                "time_left": 0,
                "error": str(e)
            }


async def safe_api_call(url: str) -> Dict[str, Any]:
    """
    Makes a safe API call with timeouts and fallback data.
    
    Args:
        url: The URL to fetch data from
        
    Returns:
        Dict: The API response or fallback data if the call fails
    """
    try:
        timeout = httpx.Timeout(10.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError, json.JSONDecodeError) as e:
        log_error(f"API call failed: {e}")
        # Return fallback data if any error occurs
        return generate_fallback_data()


async def fetch_and_cache_time(cache_key: str, external_url: str, expire_seconds: int, redis: Optional[Any] = None):
    """
    Fetches data from an external API and optionally caches it in Redis if enabled.

    This function checks if Redis is enabled and if the data for the given cache_key is already stored in Redis.
    If so, it returns the cached data along with the remaining time to live (TTL).
    If not, it fetches the data from the specified external URL, caches it in Redis if enabled,
    and returns the fetched data along with the TTL.

    Args:
        cache_key: The key under which the data is stored in Redis.
        external_url: The URL to fetch data from if not available in cache.
        expire_seconds: The time in seconds after which the cached data expires.
        redis: The Redis client instance to interact with the cache.

    Returns:
        dict: A dictionary containing the data, the source ("cache", "api", or "no-cache"), and the TTL.
    """
    # Check cache first
    hit, data, ttl = await CacheHandler.get_cache(redis, cache_key)
    if hit:
        return {
            "data": data,
            "source": "cache",
            "time_left": ttl
        }
    
    # No cache hit, fetch from API
    time_data = await safe_api_call(external_url)
    
    # If Redis is enabled and client is available, cache the result
    if REDIS_ENABLED and redis is not None:
        try:
            return await CacheHandler.cache_result(cache_key, time_data, expire_seconds, redis)
        except Exception as e:
            log_warning(f"Failed to cache data for key {cache_key}: {e}")
            return {
                "data": time_data,
                "source": "api-fallback",
                "time_left": 0,
                "error": str(e)
            }
    else:
        return {
            "data": time_data,
            "source": "no-cache",
            "time_left": 0
        }


# Login attempts tracking for auth module
async def get_login_attempts(redis, username: str) -> int:
    """
    Retrieves the number of failed login attempts for a given username.
    
    Args:
        redis: The Redis client
        username: The username to check.
        
    Returns:
        int: The number of failed login attempts
    """
    if not REDIS_ENABLED or redis is None:
        return 0
        
    try:
        attempts = await redis.get(f"{username}:attempts")
        return int(attempts) if attempts else 0
    except Exception:
        return 0


async def get_last_attempt_time(redis, username: str) -> Optional[datetime]:
    """
    Retrieves the time of the last failed login attempt for a given username.
    
    Args:
        redis: The Redis client
        username: The username to check.
        
    Returns:
        Optional[datetime]: The datetime of the last failed login attempt or None if not found.
    """
    if not REDIS_ENABLED or redis is None:
        return None
        
    try:
        last_time = await redis.get(f"{username}:last_attempt")
        return datetime.fromtimestamp(float(last_time)) if last_time else None
    except Exception:
        return None


async def set_failed_login(redis, username: str, attempts: int, last_attempt_time: datetime) -> bool:
    """
    Sets the number of failed login attempts and the time of the last attempt for a username.
    
    Args:
        redis: The Redis client
        username: The username to update.
        attempts: The number of failed login attempts.
        last_attempt_time: The datetime of the last failed login attempt.
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not REDIS_ENABLED or redis is None:
        log_warning(f"Redis is disabled or unavailable. Failed login attempt for username: {username} not stored.")
        return False
        
    try:
        await redis.set(f"{username}:attempts", attempts, ex=300)  # 5 minutes expiration
        await redis.set(f"{username}:last_attempt", last_attempt_time.timestamp(), ex=300)
        log_warning(f"Failed login attempt for username: {username}. Attempts: {attempts}")
        return True
    except Exception as e:
        log_warning(f"Error storing failed login attempt: {e}")
        return False


async def reset_login_attempts(redis, username: str) -> bool:
    """
    Resets the failed login attempt count for a username.
    
    Args:
        redis: The Redis client
        username: The username to reset.
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not REDIS_ENABLED or redis is None:
        return False
        
    try:
        await redis.delete(f"{username}:attempts", f"{username}:last_attempt")
        log_info(f"Reset login attempts for username: {username}")
        return True
    except Exception:
        return False