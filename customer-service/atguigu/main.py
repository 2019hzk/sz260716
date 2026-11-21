"""
启动uvicorn web服务
"""

import uvicorn

from atguigu.common.event_loop import run_async
from atguigu.common.settings import get_settings


async def start_async_uvicorn():
    settings = get_settings()
    # 1. 先获取Server对象
    server = uvicorn.Server(
        uvicorn.Config(
            app="atguigu.app.app:app",
            host=settings.api_host,
            port=settings.api_port,
            loop="none"  # 一定用到指定的事件循环执行
        )
    )

    # 2. server对象的异步方法
    await server.serve()  # 和uvicorn.run实现的效果一样，启动方式换成了异步


if __name__ == '__main__':
    run_async(start_async_uvicorn())

    # uvicorn.run(app="atguigu.app.app:app", host=settings.api_host, port=settings.api_port)  # 底层使用asyncio.run(process_chat_endpoint())
