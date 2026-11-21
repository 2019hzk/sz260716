"""
处理聊天相关的路由请求
处理聊天
加载历史会话
"""
from fastapi import APIRouter
from atguigu.app.dependecies import ChatServiceDep, UserRoleDep
from atguigu.app.schams import ChatMessageRequest


router = APIRouter(prefix="/api/v1/chat", tags=["处理对话、加载历史对话的聊天路由"])


@router.post("/messages", description="处理对话")
async def process_chat_endpoint(payload: ChatMessageRequest,
                                service: ChatServiceDep,
                                user_role: UserRoleDep
                                ):
    await service.process_chat_message(payload, user_role.user_id)
    return {""}
