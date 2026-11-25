from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from atguigu.app.models.enums import HandoffStatus
from atguigu.app.models.models import Handoff, Conversation


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



