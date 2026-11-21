from typing import Annotated

from fastapi import APIRouter, Path, Query, Header
from pydantic import BaseModel

router = APIRouter(tags=["测试简单使用"])


@router.get("/hello")
async def hello():
    return {
        "success": "ok"}  # 字典对象   FastAPI自动序列化动作       json格式字符串    /反序列化   字符串（json格式字符串）转对象（字典、dataclass对应的数据模型、pydantic对应数据模型【方式】）
