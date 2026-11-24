from sqlalchemy.ext.asyncio import AsyncSession

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
