from fastapi import APIRouter, status

from atguigu.app.dependecies import AdminServiceDep, StaffRoleDep
from atguigu.app.schemas import ReplyRequest

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


@router.post("/{handoff_id}/accept", description="客服接收指定工单", status_code=status.HTTP_204_NO_CONTENT)
async def accept_handoff_endpoint(handoff_id: str,
                                  service: AdminServiceDep,
                                  staff_role: StaffRoleDep
                                  ):
    await service.accept_handoff(handoff_id, staff_role.user_id)


@router.post("/{handoff_id}/messages", description="客服回复")
async def reply_message_endpoint(handoff_id: str,
                                 payload: ReplyRequest,
                                 service: AdminServiceDep,
                                 _: StaffRoleDep  # 只做校验
                                 ):
    await service.reply_message(handoff_id, payload)
