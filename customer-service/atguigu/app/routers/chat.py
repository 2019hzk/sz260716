"""
处理聊天相关的路由请求
处理聊天
加载历史会话
"""
from typing import Any

from fastapi import APIRouter, status
from atguigu.app.dependecies import ChatServiceDep, UserRoleDep
from atguigu.app.schemas import ChatMessageRequest

router = APIRouter(prefix="/api/v1/chat", tags=["处理对话、加载历史对话的聊天路由"])


@router.post("/messages", description="处理对话", status_code=status.HTTP_204_NO_CONTENT)
async def process_chat_endpoint(payload: ChatMessageRequest,
                                service: ChatServiceDep,
                                user_role: UserRoleDep
                                ):
    await service.process_chat_message(payload, user_role.user_id)


@router.get("/history", description="获取当前用户的所有会话下的消息")
async def get_chat_history_endpoint(
        service: ChatServiceDep,
        user_role: UserRoleDep
) -> dict[str, Any]:
    return await  service.get_chat_history(user_role.user_id)
