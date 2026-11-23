"""
服务组件(处理逻辑)
"""
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from atguigu.app.models.enums import MessageRole, ConversationMode, TurnStatus
from atguigu.app.models.models import Message, Conversation, ConversationTurn
from atguigu.app.schemas import ChatMessageRequest
from atguigu.app.services.realtime import RealTimeService
from atguigu.common.utils import get_utcnow, get_uid
from atguigu.common.settings import get_settings


class ChatService:

    def __init__(self, session: AsyncSession):
        self._session = session
        self._settings = get_settings()
        self._realtime_service = RealTimeService(session)

    async def get_chat_history(self, user_id: str) -> dict[str, Any]:
        """
        职责: 返回当前用户下所有会话的消息
        :param user_id:
        :return:
        dict[str,Any]:存储三部分信息
        "messages":[当前用户所有会话下的消息]
        "conversation_id": 当前用户活跃会话的ID
        "conversation_mode":当前用户活跃会话的模式
        """
        # 1. 查询当前用户所有会话下的[消息]
        # 1.1 构建SQL语句
        stmt = (select(Message)
                .join(Conversation, Conversation.id == Message.conversation_id)
                .where(
            Conversation.user_id == user_id
        ).order_by(Message.id))

        # 1.2 执行SQL语句
        records = (await  self._session.scalars(stmt)).all()

        # 2. 构建当前用户所有会话下的消息列表
        messages = [
            {
                "conversation_id": record.conversation_id,  # 每一条消息对应的会话ID(即有活跃的会话ID 也会有已经关闭的会话ID)
                "role": record.role,  # 每一条消息的角色(USER/AI/HUMAN)
                "content": record.content  # 每一天消息的内容(用户发送的内容、AI的回复、人工客服的回复)
            }
            for record in records
        ]

        # 3. 获取当前用户活跃会话的ID和模式
        active_conversation = await self._get_or_create_conversation(user_id)

        # 4. 返回接口需要的数据结构
        return {
            "conversation_id": active_conversation.id,
            "conversation_mode": active_conversation.mode,  # 保证用户端右上角的徽章模式初始的时候状态更新
            "messages": messages
        }

    async def process_chat_message(self, payload: ChatMessageRequest, user_id: str):
        """
        职责：真正处理对话。对数据库做[写]。 三张表的初始化
        :param payload:
        :param user_id:
        :return:
        """

        # 1. 重复消息去重[重试同一条消息：message_id是一样的]
        # 1.1 构建查询消息的SQL语句
        stmt = select(Message).where(Message.message_id == payload.message_id)
        # 1.2 执行SQL语句
        message = await self._session.scalar(stmt)

        if message:
            return

        # 2. 确保存在活跃会话
        conversation = await self._get_or_create_conversation(user_id)

        # 3. 构建用户角色的消息对象，并且add到数据库中
        message = Message(
            message_id=payload.message_id,
            conversation_id=conversation.id,
            role=MessageRole.USER,
            message_type=payload.type,
            content=payload.content
        )
        self._session.add(message)  # 没刷盘
        conversation.last_active_at = get_utcnow()  # 更新当前会话的最后一次激活时间

        # 4. 根据会话模式分流
        if conversation.mode == ConversationMode.AI:
            # AI_Worker处理的：交给AI 智能体处理（调用AI-Service接口，结果在获取到，判断是否插话，如果插话，修改轮次状态。如果没插话，存储结果）
            await self._create_turn(conversation.id)
        else:
            # 会话模式要不是QUEUED[等待人工客服]/HUMAN【人工客服服务中】
            # 交给人工客服处理---链路很长(点击看工单、接入工单、回复工单、结束工单)
            # 发送一个能够让前端调用查询工单项的接口信号。（为了后续真正处理工单的条件）ws

            self._realtime_service.add_events(message,conversation,notify_staff=True)

        # 5. 统一提交
        await self._session.commit()

    async def _get_or_create_conversation(self, user_id: str) -> Conversation:
        """
        职责： 返回一个活跃的会话对象
        :param user_id:
        :return:
        """

        # 1. 查询当前用户活跃会话
        # 1.1 构建查询当前用户活跃会话的SQL语句
        stmt = select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.mode != ConversationMode.CLOSED
        )

        # 1.2 执行SQL语句
        conversation = await self._session.scalar(stmt)  # Conversation对象 or None对象

        # 2. 存在有效的会话
        if conversation:
            # a. 判断当前会话是否依然有效(AI模式&&比较时间)
            timeout = timedelta(minutes=self._settings.conversation_idle_timeout_minutes)
            if conversation.mode == ConversationMode.AI and get_utcnow() - conversation.last_active_at >= timeout:
                conversation.mode = ConversationMode.CLOSED  # 当前的会话模式修改为非活跃状态
            # b.   当前会话是有效的，直接返回
            else:
                return conversation

        # 3. 创建一个活跃的会话对象
        conversation = Conversation(id=get_uid("con"), user_id=user_id, mode=ConversationMode.AI)  # id:单独给一次值
        self._session.add(conversation)

        # 4. 返回活跃的会话
        return conversation

    async def _create_turn(self, conversation_id: str) -> ConversationTurn:
        """
        职责：创建COLLECTING待收集状态的轮次
        :param conversation_id:
        :return:
        """
        # 1. 查询待收集状态的轮次
        # 1.1 定义SQL语句
        stmt = select(ConversationTurn).where(
            ConversationTurn.conversation_id == conversation_id,
            ConversationTurn.status == TurnStatus.COLLECTING
        )
        # 2. 查询轮次
        turn = await  self._session.scalar(stmt)

        # 3. 创建新收集状态的轮次
        if turn is None:
            turn = ConversationTurn(conversation_id=conversation_id, status=TurnStatus.COLLECTING,
                                    collect_until=get_utcnow() + timedelta(self._settings.message_merge_delay_ms))
            self._session.add(turn)

        # 4. 返回收集状态的轮次
        return turn
