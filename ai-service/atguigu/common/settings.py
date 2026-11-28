from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """AI Service 运行配置"""

    database_url: str = Field(
        "postgresql+psycopg://customer_service:customer_service@127.0.0.1:5432/ai_customer_service",
        description="AI 服务 PostgreSQL 数据库连接地址",
    )
    api_host: str = Field("0.0.0.0", description="服务监听地址")
    api_port: int = Field(8002, description="服务监听端口")
    internal_service_token: str = Field("customer-internal-token", description="微服务内部调用共享令牌")
    jwt_secret: str = Field("ecommerce-secret", description="JWT 签名密钥")
    jwt_algorithm: str = Field("HS256", description="JWT 签名算法")
    ecommerce_base_url: str = Field("http://127.0.0.1:8001/api/v1", description="电商业务服务接口地址")
    ecommerce_timeout_seconds: float = Field(8.0, description="调用电商业务服务的 HTTP 超时秒数")

    llm_provider: Literal["deepseek", "qwen"] = Field(
        "deepseek",
        description="大模型提供商类型",
    )
    llm_model: str = Field("deepseek-chat", description="主模型（DeepSeek）名称")
    llm_api_key: str = Field("", description="主模型 API Key")
    llm_base_url: str = Field("https://api.deepseek.com", description="主模型接口基础地址")
    llm_timeout_seconds: float = Field(15.0, description="单次调用大模型的超时秒数")
    llm_max_retries: int = Field(0, description="主模型调用失败时的 SDK 内部重试次数（0 表示失败立即回退到备用模型）")

    llm_fallback_model: str = Field("qwen3.8-max-0902", description="备用大模型名称")
    llm_fallback_max_retries: int = Field(1, description="备用模型调用失败时的 SDK 内部重试次数")
    llm_fallback_api_key: str = Field("", description="备用大模型 API Key")
    llm_fallback_base_url: str = Field(
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="备用大模型接口基础地址（OpenAI 兼容模式）",
    )
    history_message_limit: int = Field(30, description="注入上下文的最大历史消息条数")
    history_character_budget: int = Field(12000, description="注入上下文的最大历史字符预算")
    prompt_version: str = Field("customer-support-v1", description="当前系统提示词版本号")

    typesafe_api_key: str = Field("", description="TypeSafe Jev 模型 API Key")
    typesafe_base_url: str = Field("https://api.typesafe.ai", description="TypeSafe Jev 接口基础地址")
    typesafe_model: str = Field("jev-latest", description="TypeSafe System One 决策模型名称")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
