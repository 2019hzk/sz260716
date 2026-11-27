from typing import Any, Literal

from pydantic import BaseModel, Field


class CurrentUser(BaseModel):
    user_id: str
    role: Literal["user", "admin"]


class AgentRunRequest(BaseModel):
    conversation_id: str
    message: list[dict[str, Any]]
    history: list[dict[str, Any]]
