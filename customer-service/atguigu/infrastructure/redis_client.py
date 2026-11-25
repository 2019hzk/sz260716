
from redis.asyncio.client import Redis

# # 定义Redis客户端
redis_client = Redis.from_url(url="redis://192.168.200.158:6379/0", decode_responses=True)


