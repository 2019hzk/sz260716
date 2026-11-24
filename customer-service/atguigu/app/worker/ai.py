"""
负责处理消息
"""
import asyncio
import logging
from typing import Any

from atguigu.app.models.models import ConversationTurn
from atguigu.app.services.chat import ChatService
from atguigu.common.settings import get_settings
from atguigu.infrastructure.db import AsyncSessionFactory

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class AIWorker:

    def __init__(self):

        self._settings = get_settings()
        self._session_factory = AsyncSessionFactory

    async def start(self):
        """
        职责：主轮询方法的入口
        :return:
        """
        logger.info("AI Worker已启动")

        while True:
            claimed_turn = await self._claim_process_turn()
            # 没有领取到，休眠一会，为了防止cpu空转
            if not claimed_turn:
                await asyncio.sleep(self._settings.ai_worker_poll_interval_ms / 1000)  # 100ms

    async def _claim_process_turn(self) -> bool:
        """
        职责：领取轮次并且处理领到的轮次
        :return:
        """

        async  with  self._session_factory() as session:
            # 1. 实例化ChatService
            chat_service = ChatService(session)

            # 2. 领取轮次并且组装AI Service请求的载荷数据
            claimed_turn_payload: tuple[ConversationTurn, dict[
                str, Any]] | None = await chat_service.claim_turn_build_payload()
            if claimed_turn_payload is None:
                return False

            # 3. 解包claimed_turn_payload--->tuple[claimed_turn,payload]
            claimed_turn, payload = claimed_turn_payload

            # 4. 调用AI Service
            ai_result = await self._call_ai_service(payload)

            # 5. 处理AI Service结果、以及修改轮次的终态
            await chat_service.finish_turn()

            return True
