"""
服务组件(处理逻辑)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from atguigu.app.models.enums import MessageRole, ConversationMode
from atguigu.app.models.models import Message
from atguigu.app.schams import ChatMessageRequest
from atguigu.common.utils import get_utcnow


class ChatService:

    def __init__(self, session: AsyncSession):
        self._session = session

    async def process_chat_message(self, payload: ChatMessageRequest):
        """
        职责：真正处理对话。对数据库做[写]。 三张表的初始化
        :param payload:
        :return:
        """

        # 1. 重复消息去重[重试同一条消息：message_id是一样的]
        # 1.1 构建查询消息的SQL语句
        stmt= select(Message).where(Message.message_id== payload.message_id)
        # 1.2 执行SQL语句
        message= await self._session.scalar(stmt)

        if message:
            return


        # 2. 确保存在活跃会话
        conversation= self._get_or_create_conversation()


        # 3. 构建用户角色的消息对象，并且add到数据库中
        message= Message(
            message_id=payload.message_id,
            conversation_id=conversation.id,
            role=MessageRole.USER,
            message_type=payload.type,
            content=payload.content
        )
        self._session.add(message)  # 没刷盘
        conversation.last_active_at=get_utcnow()  # 更新当前会话的最后一次激活时间

        # 4. 根据会话模式分流
        if conversation.mode== ConversationMode.AI:
            # 交给AI 智能体处理
            pass
        else:
            # 交给人工客服处理
            pass


        # 5. 统一提交
        await self._session.commit()
















