from fastapi import APIRouter, status

from atguigu.app.dependecies import AdminServiceDep, StaffRoleDep

router = APIRouter(prefix="/api/v1/handoffs", tags=["管理端对应的路由"])


@router.get("", description="查询有效状态的工单列表")
async def handoffs_endpoint(
        service: AdminServiceDep,
        _: StaffRoleDep  # 只做校验
):
    return await service.get_handoffs()


@router.get("/{handoff_id}/messages", description="查询指定工单对应的会话下所有消息")
async def get_messages_endpoint(handoff_id: str,
                                service: AdminServiceDep,
                                _: StaffRoleDep  # 只做校验
                                ):
    return await service.get_messages(handoff_id)


@router.get("/{handoff_id}/accept", description="客服接收指定工单")
async def accept_handoff_endpoint(handoff_id: str,
                                  service: AdminServiceDep,
                                  staff_role: StaffRoleDep
                                  ):
    await service.accept_handoff(handoff_id, staff_role.user_id)
