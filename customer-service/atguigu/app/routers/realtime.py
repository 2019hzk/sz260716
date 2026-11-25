import asyncio
import logging
from asyncio import FIRST_COMPLETED
from typing import Any

from fastapi import APIRouter, WebSocket, status
from atguigu.infrastructure.redis_client import redis_client

from atguigu.app.services.auth import decode_access_token

router = APIRouter(prefix="/api/v1", tags=["实时事件订阅者路由"])


@router.websocket("/realtime")
async def realtime(ws: WebSocket):
    """

    :return:
    """

    # 1. 确保建立好ws通道
    await ws.accept()

    # 2. 从ws通道中获取客户端发送的令牌token
    access_token = ""
    try:
        user_info: dict[str, Any] = await ws.receive_json()
        access_token = user_info['token']
    except Exception as exc:
        logging.exception(f"用户认证信息获取失败原因%s", str(exc))
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="用户未认证")  # 关闭通道
        return

        #  3. 根据用户令牌获取用户信息
    current_user = decode_access_token(access_token)

    # 4. 用户的角色确定通道
    target_channel = current_user.user_id if current_user.role == "user" else "staff"

    # 5. 连通服务中图标
    await ws.send_json({"event_type": "connected"})

    # 6. 注册通道到redis
    async with redis_client.pubsub() as pubsub:
        # 6.1 注册目标通道
        await pubsub.subscribe(target_channel)

        # 6.2 定会转发通道数据协程任务
        async def event_forward():
            """
            职责：将通道的数据 转发到ws通道中推送给前端
            :return:
            """
            async  for message in pubsub.listen():  # Redis宕机了，出现RedisError
                # 过滤业务数据
                if message['type'] == "message":
                    channel_data = message["data"]
                    await ws.send_text(channel_data)

        # 6.3 定义从ws通道中获取数据
        async def listen_ws():
            """
            职责：从ws通道中获取数据。【获取数据，监听前端有没有手动将ws通道关闭。【关闭浏览器或者页面】】
            :return:
            """
            while True:
                await ws.receive_text()  # DisconnectedError

        # 6.4 并发启动两个协程任务执行 且把这两个协程任务对象收集到了列表中
        tasks = [
            asyncio.create_task(event_forward()),
            asyncio.create_task(listen_ws()),
        ]

        # done:做完的（死掉的协程任务）列表
        # pending：在活着协程任务列表

        # 6.5 监控两个协程任务执行情况
        done, pending = await asyncio.wait(tasks,
                                           return_when=FIRST_COMPLETED)  # 当什么条件满足的时候 别等了(任意一个协程任务做完【1.正常执行完 2. 出现异常】，就别等了)

        # 6.6 取消未完成的协程任务
        for p in pending:
            p.cancel()  # 发送了一个取消协程任务的信号而已：CanneledError（await 处）

        # 6.7 真正让未做完的协程任务(取消掉)且异常静默处理
        await asyncio.gather(*tasks, return_exceptions=True)  # 真正让未做完的协程任务(取消掉)

    # 资源清理动作-----------优雅关闭--------------

    # 两个通管 通道一（ws） 通道二 （redis）
    # ws通道关闭，redis通道没有必要在保留(订阅者取消掉，redis客户端释放)
    # redis订阅准备取消掉或者redis客户端释放(redis宕机了)，ws通道关闭掉。
    # 二者要同时存活才有意义，只要有一方出现了问题，另外一方没有必要在存活。（同生共死）
    # 魔法棒：监控器监控二者。一方死了 ，死的人给我  活人也给我
    # 自己手动的把活的人给kill杀死。
