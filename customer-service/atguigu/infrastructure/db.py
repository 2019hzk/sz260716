"""
管理数据库操作
1. 创建引擎
2. 创建SessionFactory
3. with 上下文对象获取session对象
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker,AsyncSession
from atguigu.common.settings import get_settings

# 1. 创建异步引擎
engine = create_async_engine(url=get_settings().database_url, echo=False)

# 2. 创建异步session工厂
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async  def get_async_session()->AsyncGenerator[AsyncSession]:
    """
    职责：从session工厂中返回session
    :return:
    """

    async  with  AsyncSessionFactory() as session:
        # 1. 谁去用----FastAPI用
        # 2. 怎么才能回来----FASTAPI(接口准备返回前)在回来

        yield  session   # yield出去，session工厂的资源释放动作(关闭session无法做)
