from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from db.clientRedis import AsyncRedisClient
import httpx
import json

router = APIRouter()


# sample usage with external API and Redis
async def fetch_and_cache_time(cache_key: str, external_url: str, expire_seconds: int, redis: Redis):
    """
    Fetches data from an external API and caches it in Redis.

    This function checks if the data for the given cache_key is already stored in Redis.
    If so, it returns the cached data along with the remaining time to live (TTL).
    If not, it fetches the data from the specified external URL, caches it in Redis,
    and returns the fetched data along with the TTL.

    The data is stored in Redis in JSON format to maintain structure and readability.

    Args:
        cache_key (str): The key under which the data is stored in Redis.
        external_url (str): The URL to fetch data from if not available in cache.
        expire_seconds (int): The time in seconds after which the cached data expires.
        redis (Redis): The Redis client instance to interact with the cache.

    Returns:
        dict: A dictionary containing the data, the source ("cache" or "api"), and the TTL.
    """
    cached_data = await redis.get(cache_key)

    if cached_data:
        ttl = await redis.ttl(cache_key)
        return {
            "data": json.loads(cached_data),  # Decode JSON data
            "source": "cache",
            "time_left": ttl
        }
    else:
        async with httpx.AsyncClient() as client:
            response = await client.get(external_url)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        time_data = response.json()  # Parse the response as JSON
        await redis.set(cache_key, json.dumps(time_data), ex=expire_seconds)

        return {
            "data": time_data,
            "source": "api",
            "time_left": expire_seconds
        }


@router.get("/hello")
async def say_hello(redis: Redis = Depends(AsyncRedisClient.get_instance)):
    cache_key = "current_utc_time"
    expire_seconds = 60  # Example expiration time
    time_api = "https://worldtimeapi.org/api/timezone/etc/utc"  # Example URL to get UTC time

    time_info = await fetch_and_cache_time(cache_key, time_api, expire_seconds, redis)

    return {
        "message": "Hello",
        "source": time_info["source"],
        "time_left": time_info["time_left"],
        "data": time_info["data"]
    }
