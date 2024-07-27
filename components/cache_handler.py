from redis.asyncio import Redis


async def cache_result(cache_key: str, result: str, expire_seconds: int, redis: Redis):
    """
    Caches a result in Redis and returns cache details.

    This function stores the given result in the Redis cache under the specified
    cache_key with an expiration time of expire_seconds. It then retrieves the
    time-to-live (TTL) for the cache key and returns the data along with the source
    information and TTL.

    Args:
        cache_key (str): The key under which the result will be stored in Redis.
        result (str): The result data to be cached.
        expire_seconds (int): The time in seconds after which the cache entry will expire.
        redis (Redis): The Redis client instance to interact with the cache.

    Returns:
        dict: A dictionary containing the cached data, the source ("cache"), and the TTL.
    """
    await redis.set(cache_key, result, ex=expire_seconds)
    ttl = await redis.ttl(cache_key)
    return {
        "data": result,
        "source": "cache",
        "time_left": ttl
    }
