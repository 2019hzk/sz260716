"""
模块：主要映射.env文件的key,value
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

ENV_FILE_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """
    配置类
    """
    database_url: str = Field("postgresql+psycopg://customer_service:customer_service@locahost:5432/customer_service",
                              description="PgSQL数据库的url地址信息")
    jwt_secret: str = Field("demo-secret", description="jwt加密、解密时对应的秘钥")
    jwt_algorithm: str = Field("HS512", description="jwt加密、解密时对应的算法")
    api_host: str = Field("localhost", description="customer-service服务的域名/ip")
    api_port: int = Field("8080", description="customer-service服务端口")
    cors_origins: list[str] = Field(
        ["http://localhost:5173",
         "http://127.0.0.1:5173",
         "http://localhost:5174",
         "http://127.0.0.1:5174"], description="跨域允许的源")

    conversation_idle_timeout_minutes: int = Field(30, description="AI模式下会话的有效时间")
    message_merge_delay_ms: int = Field(30, description="AI模式下消息的防抖时间窗口阈值")
    # 变量名字必须叫model_config
    model_config = SettingsConfigDict(env_file=ENV_FILE_PATH, extra="ignore")


@lru_cache  # 1. 缓存【key,value】缓存的key:方法对象 缓存的value：方法的返回值    {"ox1234","0x22234"},lru：最近最少未使用的淘汰走
def get_settings() -> Settings:
    """
    职责：返回Settings 实例对象
    :return:
    """
    return Settings()
