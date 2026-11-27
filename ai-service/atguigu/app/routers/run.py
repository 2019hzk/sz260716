from typing import Annotated, Any
from fastapi import APIRouter, Depends

from atguigu.app.dependencies import UserDep, require_internal_service
from atguigu.app.schemas import AgentRunRequest

router = APIRouter(tags=["Ai Service 运行路由"])


@router.post("/internal/v1/agent/runs")
async def start_run_endpoint(payload: AgentRunRequest,
                             current_user: UserDep,
                             _: Annotated[None, Depends(require_internal_service)],
                             ) -> dict[str, Any]:
    return {}
