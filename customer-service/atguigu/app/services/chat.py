"""
服务组件(处理逻辑)
"""
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from atguigu.app.models.enums import MessageRole, ConversationMode, TurnStatus
from atguigu.app.models.models import Message, Conversation, ConversationTurn
from atguigu.app.schams import ChatMessageRequest
from atguigu.common.utils import get_utcnow, get_uid
from atguigu.common.settings import get_settings


class ChatService:

    def __init__(self, session: AsyncSession):
        self._session = session
        self._settings = get_settings()

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
            # 交给人工客服处理
            pass

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

        turn = await  self._session.scalar(stmt)
        if turn is None:
            turn = ConversationTurn(conversation_id=conversation_id,status=TurnStatus.COLLECTING,collect_until=get_utcnow()+timedelta(self._settings.message_merge_delay_ms))
            self._session.add(turn)

        return  turn
