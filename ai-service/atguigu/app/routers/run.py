from typing import Annotated, Any
from fastapi import APIRouter, Depends,Request

from atguigu.app.dependencies import UserDep, require_internal_service, AgentExecuteDep
from atguigu.app.schemas import AgentRunRequest
router = APIRouter(tags=["Ai Service 运行路由"])


@router.post("/internal/v1/agent/runs")
async def start_run_endpoint(payload: AgentRunRequest,
                             current_user: UserDep,
                             _: Annotated[None, Depends(require_internal_service)],
                             agent_executor: AgentExecuteDep,
                             ) -> dict[str, Any]:


    ai_result = await agent_executor.start_run()
    return ai_result



