from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from atguigu.app.models.enums import HandoffStatus, ConversationMode, MessageRole
from atguigu.app.models.models import Handoff, Conversation, Message
from atguigu.app.schemas import ReplyRequest
from atguigu.app.services.realtime import RealTimeService
from atguigu.common.utils import get_uid, get_utcnow


class AdminService:

    def __init__(self, session: AsyncSession):
        self._session = session
        self._realtime_service = RealTimeService(session)

    def create_handoffs(self,
                        conversation: Conversation,
                        *,
                        summary: str
                        ):
        """
        职责：创建工单
        :return:
        """

        # 1. 实例化工单数据模型
        handoffs = Handoff(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            summary=summary,  # 给客服看
            status=HandoffStatus.WAITING
        )

        # 2. 保存
        self._session.add(handoffs)

    async def get_handoffs(self) -> list[Handoff]:
        """
        职责：查询所有处于有效状态的工单列表
        :return:
        """
        # 1. 定义查询SQL语句
        stmt = select(Handoff).where(Handoff.status.in_([HandoffStatus.WAITING, HandoffStatus.ACTIVE])).order_by(
            Handoff.created_at
        )

        # 2. 执行SQL语句
        return list((await self._session.scalars(stmt)).all())

    async def get_messages(self, handoff_id: str) -> dict[str, Any]:
        """
        职责： 查询指定工单对应的会话下所有的消息
        :param handoff_id:
        :return:
        """

        # 1. 定义查询SQL语句
        stmt = select(Message).join(Handoff, Handoff.conversation_id == Message.conversation_id).where(
            Handoff.id == handoff_id
        ).order_by(Message.created_at)

        # 2. 执行SQL语句
        messages = (await self._session.scalars(stmt)).all()

        # 3. 返回消息
        return {"messages": messages}

    async def accept_handoff(self,
                             handoff_id: str,
                             staff_id: str):
        """

        职责：客服staff_id接收工单handoff_id以及给用户端 提示开场语
        :param handoff_id:  工单
        :param staff_id:    客服的ID
        :return:
        """
        # 1.根据工单ID 查询工单信息以及会话信息
        handoff, conversation = await self._get_handoff_conversation(handoff_id)  # 并发读(不会出现问题)

        # 2. 判断工单是否已经被客服接入
        if handoff.status == HandoffStatus.ACTIVE:
            # 某一个客服已经结果该工单，另外一个客服无需修改  （必须满足 先接单客服做完，提交，另外一个客服在进来，能防住）
            return

        # 3. 修改工单状态以及会话模式
        # 3.1 修改工单状态
        handoff.status = HandoffStatus.ACTIVE  # 并发覆盖写(不会出现问题)
        # 3.2 更新工单客服ID
        handoff.staff_id = staff_id  # 并发修改(会出现问题)
        # 3.3 修改会话模式
        conversation.mode = ConversationMode.HUMAN  # 并发覆盖写(不会出现问题)

        # 4. 调用保存人工的回复方法
        self.save_human_reply(conversation, reply_text=f"客服 {staff_id} 已经接入工单，请问您有什么需要帮助的?")  # 开场白

        # 5. 提交
        await self._session.commit()

    async def _get_handoff_conversation(self, handoff_id: str) -> tuple[Handoff, Conversation]:
        """
        职责：返回工单对象以及会话对象
        :param handoff_id:
        :return:
        """
        # 1. 查询工单对象
        handoff = await self._session.scalar(
            select(Handoff).where(Handoff.id == handoff_id).with_for_update())  # 为满足条件的记录添加上一把写锁。写锁特点：写写互斥。

        # 2. 查询会话对象
        conversation = await  self._session.scalar(
            select(Conversation).where(Conversation.id == handoff.conversation_id))

        # 3. 返回
        return handoff, conversation

    async def reply_message(self,
                            handoff_id: str,
                            payload: ReplyRequest):
        """
        职责： 客服回复用户的工单信息（相互聊天）
        :param handoff_id:
        :param payload:
        :return:
        """

        # 1. 查询工单对应的会话
        _, conversation = await self._get_handoff_conversation(handoff_id)

        # 2. 保存客服回复到消息表(对内)以及事实事件表(对外)
        self.save_human_reply(
            conversation,
            reply_text=payload.text  # 客服的回复内容
        )

        # 3. 统一commit
        await self._session.commit()

    def save_human_reply(self,
                         conversation: Conversation,
                         *,
                         reply_text: str
                         ):
        # 1. 构建message对象
        message = Message(
            message_id=get_uid("human"),
            conversation_id=conversation.id,
            role=MessageRole.HUMAN,
            message_type="text",
            content={"text": reply_text}
        )

        self._session.add(message)

        conversation.last_active_at = get_utcnow()

        # 2. 调用realtime_service的add_event方法(客服侧只需要通知用户端即可)
        self._realtime_service.add_events(message, conversation, notify_user=True)

    async def resolve_handoff(self, handoff_id: str):
        """
        职责：客服关闭工单以及给用户端结束语
        :param handoff_id:
        :return:
        """

        # 1. 查询工单以及会话
        handoff, conversation = await self._get_handoff_conversation(handoff_id)

        # 2. 修改工单状态
        handoff.status = HandoffStatus.RESOLVE  # 关闭

        # 3. 修改会话模式
        conversation.mode = ConversationMode.AI  # 切回AI会话模式

        # 4. 调用保存人工的回复方法
        self.save_human_reply(conversation,
                              reply_text=f"人工客服{handoff.staff_id}已经结束，稍后由AI 继续为你服务。")  # 结束语

        # 5. 提交
        await self._session.commit()
