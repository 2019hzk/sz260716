"""
创建Agent组件

"""

from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware
from atguigu.agent.llm.adapter import get_deepseek_model_client, get_qwen_model_client


def create_ai_agent():
    """
    职责：创建Agent对象.至上挂上LLM模型客户端,不是调用Agent.实例化Agent出来
    """

    return create_agent(
        model=get_deepseek_model_client(),  # 初始化的时候给Agent指定的是主模型。
        middleware=[ModelFallbackMiddleware(get_qwen_model_client())],  # 备用模型
    )
