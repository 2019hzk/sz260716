import logging
import time

from typing import Any

from langchain_core.callbacks import UsageMetadataCallbackHandler
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from langchain_core.messages import BaseMessage

from atguigu.app.models.enums import AgentTraceStatus
from atguigu.app.models.models import AgentTrace
from atguigu.app.schemas import AgentRunRequest
from atguigu.common.settings import get_settings
from atguigu.agent.harness.run.context import build_message_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentExecute:
    """
    Agent执行器（Agent执行的核心大组件）
    """

    def __init__(self,
                 session: AsyncSession,
                 *,
                 agent: Any
                 ):
        self.settings = get_settings()
        self._session = session
        self._agent = agent

    async def start_run(self, payload: AgentRunRequest) -> dict[str, Any]:
        """
        职责：
        1. IO 操作    self._session
        2. 计算操作    self._agent
        存算分离
        返回值类型是一个字典，其次给调用方customer-service使用
        """

        # 1. 实例化AgentTraces对象
        agent_traces = AgentTrace(
            conversation_id=payload.conversation_id,
            status=AgentTraceStatus.RUNNING,  # 初始状态
            model_name=self.settings.llm_model,  # 初始主模型名字
            prompt_version=self.settings.prompt_version,
        )

        # 2. 加入到数据库
        self._session.add(agent_traces)

        # 3. 提交(为什么提交提交) 目的是为了Agent 运行期间 监控平台也能看到处于运行状态的Agent轨迹
        await self._session.commit()

        # 4. 调用Agent(5s)
        start_time = time.perf_counter()
        try:
            ai_result: dict[str, Any] = await self._invoke_agent(payload, agent_traces)
        except Exception as exc:
            logger.exception(f"AI 智能体执行出错，异常原因：%s", str(exc))
            agent_traces.status = AgentTraceStatus.FAILED
            agent_traces.result = {"text": f"AI 智能体出错，异常原因:{str(exc)}"}
            agent_traces.latency_ms = int((time.perf_counter() - start_time) * 1000)
            await self._session.commit()  # 刷盘
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="AI 智能体调用失败")  # 让customer触发重试机制

        # 5. 修改Agent运行状态
        agent_traces.status = AgentTraceStatus.COMPLETED
        agent_traces.result = ai_result
        agent_traces.latency_ms = int((time.perf_counter() - start_time) * 1000)

        await self._session.commit()

        # 6. 返回智能体的结果
        return ai_result

    async def _invoke_agent(self,
                            payload: AgentRunRequest,
                            agent_traces: AgentTrace
                            ) -> dict[str, Any]:
        """
        职责：计算推理(调用LLM 异步调用)
        """
        # 1. 实例化回调处理器
        callback_handler = UsageMetadataCallbackHandler()
        try:
            # 1. 构建消息上下文
            message_context: list[BaseMessage] = build_message_context(payload)

            # 2. Agent推理计算
            agent_out: dict[str, Any] = await self._agent.ainvoke(
                {"messages": message_context},
                config={"callbacks": [callback_handler]})

            return agent_out   # finally一定会在方法退出之前执行
        # 3. 收集token用量
        finally:
            input_tokens, output_tokens = self._summary_tokens(callback_handler)
            agent_traces.input_tokens = input_tokens
            agent_traces.output_tokens = output_tokens

    def _summary_tokens(self, callback_handler: UsageMetadataCallbackHandler) -> tuple[int, int]:
        """
        职责： 获取Agent推理任务时用到所有模型的token用量
        """

        all_model_tokens = list(callback_handler.usage_metadata.values())

        input_tokens = sum(model_token.get('input_tokens', 0) for model_token in all_model_tokens)
        output_tokens = sum(model_token.get('output_tokens', 0) for model_token in all_model_tokens)

        return input_tokens, output_tokens
