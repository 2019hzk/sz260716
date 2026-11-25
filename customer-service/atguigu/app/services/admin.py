from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from atguigu.app.models.enums import HandoffStatus, ConversationMode
from atguigu.app.models.models import Handoff, Conversation, Message


class AdminService:

    def __init__(self, session: AsyncSession):
        self._session = session

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
        职责：客服staff_id接收工单handoff_id
        :param handoff_id:  工单
        :param staff_id:    客服的ID
        :return:
        """
        # 1.根据工单ID 查询工单信息以及会话信息
        handoff, conversation = await self._get_handoff_conversation(handoff_id)

        # 2. 修改工单状态以及会话模式
        # 2.1 修改工单状态
        handoff.status = HandoffStatus.ACTIVE
        # 2.2 更新工单客服ID
        handoff.staff_id = staff_id
        # 2.3 修改会话模式
        conversation.mode = ConversationMode.HUMAN
        # 3. 提交
        await self._session.commit()

    async def _get_handoff_conversation(self, handoff_id: str) -> tuple[Handoff, Conversation]:
        """
        职责：返回工单对象以及会话对象
        :param handoff_id:
        :return:
        """
        # 1. 查询工单对象
        handoff = await self._session.scalar(select(Handoff).where(Handoff.id == handoff_id))

        # 2. 查询会话对象
        conversation = await  self._session.scalar(
            select(Conversation).where(Conversation.id == handoff.conversation_id))

        # 3. 返回
        return handoff, conversation
