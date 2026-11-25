"""
契约（前端、服务端接口）
"""
from typing import Literal, Any

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    message_id: str  # 前端发送的每一条消息 都会携带上消息唯一标识[随机值]
    type: Literal["text", "object"]  # 消息的类型（"text":输入框直接输入文本 or "object":订单 or 商品卡片）
    content: dict[str, Any]  # 消息的内容(文本 or 对象 消息内容都用dict接收)


class CurrentUser(BaseModel):
    user_id: str
    role: Literal["user", "staff", "admin"] = "user"


class  ReplyRequest(BaseModel):
    text: str