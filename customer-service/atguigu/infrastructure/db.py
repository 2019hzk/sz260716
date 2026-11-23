"""
管理数据库操作
1. 创建引擎
2. 创建SessionFactory
3. with 上下文对象获取session对象
"""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from atguigu.app.models.models import Base
from atguigu.common.event_loop import run_async
from atguigu.common.settings import get_settings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 1. 创建异步引擎
engine = create_async_engine(url=get_settings().database_url, echo=False)

# 2. 创建异步session工厂
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession]:
    """
    职责：从session工厂中返回session
    :return:
    """

    async  with  AsyncSessionFactory() as session:
        # 1. 谁去用----FastAPI用
        # 2. 怎么才能回来----FASTAPI(接口准备返回前)在回来

        yield session  # yield出去，session工厂的资源释放动作(关闭session无法做)


async def init_db():
    logger.info("准备初始化customer-service的表结构")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    logger.info("初始化customer-service的表结构完成")


if __name__ == '__main__':
    run_async(init_db())
