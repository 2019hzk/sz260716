"""
服务组件(处理逻辑)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from atguigu.app.schams import ChatMessageRequest


class ChatService:

    def __init__(self, session: AsyncSession):
        self._session = session

    async def process_chat_message(self, payload: ChatMessageRequest):
        """
        职责：真正处理对话。对数据库做读写。session对象
        :param payload:
        :return:
        """

        # result = await self._session.execute(text("select 1"))  # CursorResult  # psycopg:要用
        # print(result)
        # print(result.scalar())

