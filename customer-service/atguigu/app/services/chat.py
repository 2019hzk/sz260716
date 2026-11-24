"""
服务组件(处理逻辑)
"""
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from atguigu.app.models.enums import MessageRole, ConversationMode, TurnStatus
from atguigu.app.models.models import Message, Conversation, ConversationTurn, RealtimeEvent
from atguigu.app.schemas import ChatMessageRequest
from atguigu.app.services.admin import AdminService
from atguigu.app.services.realtime import RealTimeService
from atguigu.common.utils import get_utcnow, get_uid
from atguigu.common.settings import get_settings


class ChatService:

    def __init__(self, session: AsyncSession):
        self._session = session
        self._settings = get_settings()
        self._realtime_service = RealTimeService(session)
        self._admin_service = AdminService(session)

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

        await  self._session.commit()  # fix 提交
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

            self._realtime_service.add_events(message, conversation, notify_staff=True)

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
                                    collect_until=get_utcnow() + timedelta(
                                        milliseconds=self._settings.message_merge_delay_ms))
            self._session.add(turn)

        # 4. 返回收集状态的轮次
        return turn

    # ============================================处理轮次的方法逻辑=============================================
    async def claim_turn_build_payload(self) -> tuple[ConversationTurn, dict[str, Any], str] | None:
        """
        职责： 领取满足条件的轮次以及构建调用AI Service服务的请求载荷数据
        :return:
        """
        # 1. 领取满足条件的轮次(条件一：轮次的状态是COLLECTING && 条件二：轮次的收集时间到期)
        # 1.1 构建领取满足轮次的SQL
        stmt = select(ConversationTurn).where(
            ConversationTurn.status == TurnStatus.COLLECTING,
            ConversationTurn.collect_until <= get_utcnow()
        ).order_by(ConversationTurn.created_at)

        # 1.2 执行SQL语句
        claimed_turn = await self._session.scalar(stmt)

        # 1.3 未领取到轮次
        if claimed_turn is None:
            return None

        # 2. 查询当前轮次对应的会话对象
        conversation = await self._session.scalar(
            select(Conversation).where(Conversation.id == claimed_turn.conversation_id))

        # 3. 修改领取到轮次的信息
        # 3.1 修改轮次的状态
        claimed_turn.status = TurnStatus.RUNNING
        # 3.2 修改轮次的领取次数
        claimed_turn.attempts += 1
        # 3.3 修改轮次的快照消息ID（作用：1.确定轮次消息范围的下限  2.判断用户插话的条件）
        claimed_turn.snapshot_message_id = await self._get_latest_user_message_id(str(conversation.id))

        # 4. 构建AI Service请求的载荷数据
        payload: dict[str, Any] = await self.build_request_payload(claimed_turn)

        # 5. 内部单独提交(TODO)  # 结论：释放锁
        await self._session.commit()

        # 6. 返回
        return claimed_turn, payload, str(conversation.user_id)

    async def _get_latest_user_message_id(self, conversation_id: str) -> int:
        """
        职责：获取消息表中当前轮次对应的会话下最新用户角色的消息ID
        :param conversation_id:
        :return:
        """
        stmt = select(func.max(Message.id)).where(
            Message.conversation_id == conversation_id,
            Message.role == MessageRole.USER,
        )
        return await self._session.scalar(stmt)

    async def build_request_payload(self, claimed_turn: ConversationTurn) -> dict[str, Any]:
        """
        职责：构建AI Service请求的载荷数据
        :param claimed_turn:
        :return:
        {
         "conversation_id":"",
         "message":[],
         "history":[]
        }
        """
        # 1. 查询当前轮次的消息（消息归属轮次，在真正调用ai-service请求的时候，才确定）

        # 1.1 确定当前轮次的上限(找上一轮的回复消息的最大ID,上一轮消息下限)
        # a) 构建SQL语句
        stmt = select(func.max(Message.id)).where(
            Message.conversation_id == claimed_turn.conversation_id,
            Message.role != MessageRole.USER
        )
        latest_no_user_message_id = await self._session.scalar(stmt) or 0  # 第一轮来的时候
        # 1.2 确定当前轮次的下限(快照消息ID)
        latest_user_message_id = claimed_turn.snapshot_message_id

        # 1.3 构建当前轮次的消息归属的SQL语句
        turn_stmt = select(Message).where(Message.conversation_id == claimed_turn.conversation_id,
                                          Message.id > latest_no_user_message_id,
                                          Message.id <= latest_user_message_id
                                          ).order_by(Message.id)

        # 1.4 执行当前轮次的消息归属的SQL语句
        turn_messages = (await self._session.scalars(turn_stmt)).all()

        # 2. 查询历史消息作为上下文供LLM推理当前用户任务参考信息
        history_stmt = select(Message).where(
            Message.conversation_id == claimed_turn.conversation_id,
            Message.id < turn_messages[0].id
        ).order_by(Message.id.desc()).limit(30)

        history_messages = reversed((await self._session.scalars(history_stmt)).all())

        # 3. 返回请求载荷的数据
        return {
            "conversation_id": claimed_turn.conversation_id,
            "message": [
                {
                    "content": turn_message.content,
                    "type": turn_message.message_type
                }
                for turn_message in turn_messages
            ],
            "history": [
                {
                    "content": history_message.content,
                    "type": history_message.message_type,
                    "role": history_message.role
                }
                for history_message in history_messages
            ]
        }

    async def finish_turn(self,
                          claimed_turn: ConversationTurn,
                          ai_result: dict[str, Any] | None,
                          error: Exception | None):
        """
        职责：结算轮次
        1. 修改轮次状态(COMPLETED/SUPERSEDED/FAILED)--终态
        2. 判断用户是否插话，如果插话，不会存储AI Service结果
        3. 如果没有插话，需要保存AI Service结果
        4. AI Service是否调用成功，如果没有成功，需要重试，重试次数达到，主动触发转接人工.
        :param claimed_turn:
        :param ai_result:
        :param error:
        :return:
        """

        # 1. 根据当前轮次查询对应的会话
        conversation = await  self._session.scalar(
            select(Conversation).where(Conversation.id == claimed_turn.conversation_id))

        # 2. 用户插话(维度一:这个轮次是否能用)
        if claimed_turn.snapshot_message_id != await self._get_latest_user_message_id(str(conversation.id)):
            # a) 修改当前轮次的状态为终态SUPERSEDED(修改轮次状态为过期，改轮次对应的消息，后续依然能够被新轮次拿走，之前任务没有丢)
            claimed_turn.status = TurnStatus.SUPERSEDED
            # b) 提交
            await  self._session.commit()
            # c) 结束
            return

        # 3. 维度二：这个轮次改如何使用(重试、保存回复结果)
        # 3.1 customer-service调用ai-service失败
        if error is not None:
            # a) 重试耗尽,主动触发转人工
            if claimed_turn.attempts >= self._settings.ai_worker_max_attempts:
                # a.1) 修改轮次状态
                claimed_turn.status = TurnStatus.FAILED
                # a.2) 转人工
                self._admin_service.create_handoffs(conversation,
                                                    summary="AI 服务多次调用异常，系统自动降级转接人工客服")
                # a.3) 修改当前会话模式(会话没有变)
                conversation.mode = ConversationMode.QUEUED
                self.save_ai_reply(conversation, {"text": "当前智能助手正忙，已自动为您转接人工客服处理，请稍候。"})

            # b) 重试未耗尽，继续重试
            else:
                claimed_turn.status = TurnStatus.COLLECTING
                claimed_turn.collect_until = get_utcnow() + timedelta(
                    seconds=self._settings.ai_worker_retry_delay_seconds)  # 减少无用的AI Service调用。

            # 3.2) 提交
            await  self._session.commit()
            # 3.3) 结束
            return


        claimed_turn.status = TurnStatus.COMPLETED
        # 4. 保存AI Service推理后的结果(转人工请求，业务回复)
        # 4.1 转人工的请求
        if ai_result['reply_type'] == "REQUEST_HANDOFF":
            # 打通转人工，初始化工单表即可
            # a) 初始化工单表
            self._admin_service.create_handoffs(conversation, summary=ai_result['summary'])
            # b) 修改当前会话模式(会话没有变)
            conversation.mode = ConversationMode.QUEUED

        # 4.2 业务回复
        # a) AI 回复存储到messages表（对内事实依据---单独刷新出来）
        # b) AI 回复存储到realtime_events表（对外事实推送给前端）
        self.save_ai_reply(conversation, ai_result)

        # 统一提交
        await self._session.commit()

    def save_ai_reply(self,
                      conversation: Conversation,
                      ai_result: dict[str, Any]):
        """
        职责：保存AI 回复，推送AI 回复
        如果是业务回答内容，推送给用户端即可，目的为了让用户看到业务结果。右上角徽章不用变
        如果是转人工请求，既要推送给用户端【内容区域看到转人工请求成功/右上角区域看到徽章变化】，还要推送给客服端【让客服前端调用刷新handoffs列表接口，查询出来用户的工单项】
        :param conversation:
        :param ai_result:
        :return:
        """
        # 1. 保存ai回复到messages表
        message = Message(
            message_id=get_uid("msg"),
            conversation_id=conversation.id,
            role=MessageRole.AI,
            message_type="text",
            content=ai_result
        )
        self._session.add(message)

        # 2. 修改会话的激活时间
        conversation.last_active_at = get_utcnow()

        # 3. 保存ai回复到realtime_events表
        self._realtime_service.add_events(message, conversation, notify_user=True,
                                          notify_staff=conversation.mode == ConversationMode.QUEUED)
