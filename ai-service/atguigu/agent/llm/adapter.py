"""
适配不用提供商的模型：
要求模型返回的都不是纯文本，都是结构化对象。（必选）
"""
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI

from atguigu.common.settings import get_settings


def get_deepseek_model_client():
    """
    职责：返回DeepSeek模型客户端(主模型)
    如果想让模型返回结构化数据，一定要关闭掉思考模式。
    下游直接处理结构化数据最方便。

    """
    return ChatDeepSeek(
        model=get_settings().llm_model,
        api_key=get_settings().llm_api_key,  # type:ignore
        base_url=get_settings().llm_base_url,
        timeout=get_settings().llm_timeout_seconds,
        max_retries=get_settings().llm_max_retries,
        extra_body={  # deepseek关闭思考模式的写法
            "thinking": {
                "type": "disabled"
            }
        }
    )


def get_qwen_model_client():
    """
    职责：返回ChatOpen模型客户端[model="qwen3.8-max-0902"](备用模型)
    下游直接处理结构化数据最方便。
    不要单独关闭思考模式:qwen3.8-max-0902

    """
    return ChatOpenAI(
        model=get_settings().llm_fallback_model,
        api_key=get_settings().llm_fallback_api_key,  # type:ignore
        base_url=get_settings().llm_fallback_base_url,
        timeout=get_settings().llm_timeout_seconds,
        max_retries=get_settings().llm_fallback_max_retries
    )
