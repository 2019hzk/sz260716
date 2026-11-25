"""
职责：负责轮询查找待发布的事件 推送到Redis通道中


"""
import asyncio
import json
import logging
from redis import RedisError
from atguigu.app.services.realtime import RealTimeService
from atguigu.common.settings import get_settings
from atguigu.infrastructure.db import async_sessionmaker
from atguigu.infrastructure.redis_client import redis_client

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class RealtimeWorker:

    def __init__(self):
        self._settings = get_settings()
        self._session_factory = async_sessionmaker
        self._redis_client = redis_client

    async def start(self):
        logger.info("Realtime Worker已启动")

        while True:
            claimed_event = await self._claim_process_event()
            # 没有领取到，休眠一会，为了防止cpu空转
            if not claimed_event:
                await asyncio.sleep(1)  # 1s

    async def _claim_process_event(self) -> bool:
        """
        职责：负责领取待发布的事件，发布到redis通道，修改该事件为已发布
        :return:
        """
        async  with  self._session_factory() as session:
            # 1. 实例化RealTimeService
            realtime_service = RealTimeService(session)

            # 2. 查询待发布的事件
            event = await  realtime_service.get_unpublish_event()

            if event is None:
                return False

            # 确定通道
            channel = event.target
            # 确定通道数据
            channel_data = event.data

            # 3. 发布到Redis通道  (通道,通道数据)
            try:
                await self._redis_client.publish(channel, json.dumps(channel_data))
            except RedisError as exc:
                logger.exception("发布事件到Redis通道%s失败,原因:%s", channel, str(exc))
                return False

            # 4. 标记该事件已经发布
            await realtime_service.mark_published(event)

            # 5. 返回True
            return True
