import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atguigu.app.routers import chat, admin, realtime
from atguigu.app.worker.ai import AIWorker
from atguigu.app.worker.realtime import RealtimeWorker
from atguigu.common.settings import get_settings


async def lifespan(app: FastAPI):
    # 应用启动之前，先启动两个worker工作(AIWorker---轮询扫描turns表：请求AI Service；RealtimeWorker---扫描realtime_events表---事实推送数据)
    asyncio.create_task(AIWorker().start())
    asyncio.create_task(RealtimeWorker().start())

    yield  # fastapi处理路由请求

    # print("yyyyyyyy")  # 应用关闭之前执行


app = FastAPI(description="应用的FastAPI实例对象", lifespan=lifespan)

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
