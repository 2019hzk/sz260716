from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atguigu.app.routers import chat, admin, realtime
from atguigu.common.settings import get_settings

app = FastAPI(description="应用的FastAPI实例对象")

app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(realtime.router)
