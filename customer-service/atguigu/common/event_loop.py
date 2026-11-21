import asyncio
import  selectors
from collections.abc import Coroutine


def run_async(coro: Coroutine):
    """
    职责：将传入的协程对象用指定的事件循环执行
    :param coro:
    :return:
    """
    asyncio.run(coro, loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
