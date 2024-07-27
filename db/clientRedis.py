import redis.asyncio as aioredis

class AsyncRedisClient:
    _instance = None

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            cls._instance = await cls.create_redis_client()
        return cls._instance

    @staticmethod
    async def create_redis_client():
        hosts = ['localhost', 'redis', '0.0.0.0']
        for host in hosts:
            try:
                redis_client = aioredis.StrictRedis(host=host, port=6379, db=0, decode_responses=True)
                if await redis_client.ping():
                    print(f"Successfully connected to Redis server at {host}")
                    return redis_client
            except aioredis.ConnectionError as e:
                print(f"Could not connect to Redis server at {host}: {e}.")
        raise Exception("Could not connect to any Redis server.")
