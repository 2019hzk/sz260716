from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from atguigu.app.models.models import Message, Conversation, RealtimeEvent
from atguigu.common.utils import get_utcnow


class RealTimeService:

    def __init__(self, session: AsyncSession):
        self._session = session

    def add_events(self,
                   message: Message,
                   conversation: Conversation,
                   *,
                   notify_user: bool = False,
                   notify_staff: bool = False
                   ):
        """

        职责：像事实事件表中插入数据
        add_events()方法调用方，不固定，只要任意位置想要把服务端数据给某一个端【用户端、客服端】，都会调用add_events
        用户端：add_events（），将AI推理后的结果推送给用户
        客服端：add_events（），人工回复用户消息的时候。
        :param message:
        :param conversation:
        :param notify_user:
        :param notify_staff:
        :return:
        """

        # 1. 确定事实事件给哪个通道
        target_channels = []
        if notify_user:
            target_channels.append(conversation.user_id)
        if notify_staff:
            target_channels.append("staff")

        # 2. 给某一个通道的数据是什么(数据结构都是一样:dict[str,Any]三个key)
        channel_data = {
            "conversation_mode": conversation.mode,  # 当前会话对应的模式(保证用户端右上角的徽章模式实时更新)
            "role": message.role,  # 消息角色
            "content": message.content  # 消息内容
        }

        # 3. 遍历目标通道，放数据
        for target_channel in target_channels:
            self._session.add(RealtimeEvent(
                target=target_channel,
                data=channel_data
            ))

    async def get_unpublish_event(self):
        """
        职责：领取待发布的事件
        :return:
        """
        stmt = select(RealtimeEvent).where(RealtimeEvent.published_at.is_(None)).order_by(RealtimeEvent.id)
        return await self._session.scalar(stmt)

    async def mark_published(self, event: RealtimeEvent):

        # 修改
        event.published_at = get_utcnow()
        # 刷盘
        await  self._session.commit()
