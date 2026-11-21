"""

负责：将业务组件进行统一实例化和管理
"""
from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Header

from atguigu.app.schams import CurrentUser
from atguigu.app.services.auth import authorized_user
from atguigu.app.services.chat import ChatService
from atguigu.infrastructure.db import get_async_session

SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


def get_chat_service(session: SessionDep) -> ChatService:
    return ChatService(session=session)


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]


def required_user_role(authorization: Annotated[str | None, Header()]) -> CurrentUser:
    return authorized_user(authorization, "user")


UserRoleDep = Annotated[CurrentUser, Depends(required_user_role)]
