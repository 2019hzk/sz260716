# 导包的规范---三类
# 1. sdk
import asyncio
import selectors
from asyncio import WindowsSelectorEventLoopPolicy

# 2. 三方提供

# 3. 自己提供的

from sqlalchemy import String, select

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from atguigu.common.event_loop import run_async
from atguigu.common.settings import get_settings

# 1. 创建异步引擎（async异步  sync同步）
engine = create_async_engine(url=get_settings().database_url, echo=False)

# 2. 创建异步session工厂
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)  # 强烈建议设置为False.


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    # 自增主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(20))

    def __repr__(self):
        return f"id:{self.id},name:{self.name}"


async def select_demo():
    async with AsyncSessionFactory() as session:
        print("1. 新增")
        user = User(name="张三")
        session.add(user)
        await session.commit()

        print("2. 查询")
        stmt = select(User)
        db_user = (await session.scalars(stmt)).all()  # 必须加()
        print(f"查询结果: {db_user}")


async def compare_expire_on_commit():
    async with AsyncSessionFactory() as session:
        user_tom = User(name="Tom")
        session.add(user_tom)
        await session.commit()  # 数据立刻就有该条记录

        # expire_on_commit:True.当提交完毕之后 sqlalchemy，会将内存中user_tom对象的属性全部擦除
        try:
            print(
                f"尝试在 commit 后直接读取属性: user_tom.id = {user_tom.name}")  # sqlalchemy 自己去用异步连接查询数据库，把数据库最新属性返回给你。
        except Exception as e:
            print(f"原因：commit 后属性已过期，异步环境禁止隐式发起同步查询！\n   报错详情: {e}")


async def main():
    # 1. 初始化建表
    # Base.metadata.create_all(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # drop_all:删除表   :run_sync()--->向外对接的是异步连接，向内包裹的是同步函数对象
        await conn.run_sync(Base.metadata.create_all) # create_all:创建表 都是同步操作

    # 2. 运行select
    # await select_demo()

    await compare_expire_on_commit()

    # 4. 关闭引擎
    await engine.dispose()


if __name__ == '__main__':
    run_async(main())

# 原因：“windows"平台使用的事件循环【ProactorEventLoop】不能和第三方驱动psycopg做兼容。---》操作系统层面的事件循环，所有系统都支持
# 1.python-sdk:提供了能够让程序获取底层操作系统层面的事件循环对象。只需要从selectors包下获取即可。
# 2.如何放进去
# asyncio.run(main())   # 首推

# 方案一：3.12版本及以后使用的方式（针对某一个协程对象，使用指定的事件循环对象）   # 首推
# asyncio.run(main(),loop_factory=lambda : asyncio.SelectorEventLoop(selectors.SelectSelector()))

# run_async(main())   # 封装好了之后可以直接使用

# 方案二  3.11版本以前推荐的写法（全局角度替换）
# asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())


# commit 成功后，若 expire_on_commit=True
# SQLAlchemy 会把 user_tom 内存里的属性全部清空（标记为过期）
# 当在访问 user_tom.name 时，SQLAlchemy 发现这个属性处于“过期”状态，会自动在后台偷偷发一条SQL去数据库把最新数据重新拉回来填进属性里。
# 同步环境下，这一步是无感
# 异步环境下，因为访问属性 user_tom.name 是普通同步语法（不能写 await），SQLAlchemy 无法在同步属性访问器里隐式执行异步 I/O 查询，所以直接抛出异常
