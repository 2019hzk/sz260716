from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class AgentExecute:
    """
    Agent执行器（Agent执行的核心大组件）
    """

    def __init__(self,
                 session: AsyncSession,
                 *,
                 agent: Any
                 ):
        self._session = session
        self._agent = agent

    async def start_run(self):
        """
        职责：
        1. IO 操作    self._session
        2. 计算操作    self._agent
        存算分离
        """


