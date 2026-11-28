import json
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from atguigu.app.schemas import AgentRunRequest
from atguigu.common.settings import get_settings





def build_message_context(payload: AgentRunRequest) -> list[BaseMessage]:
    """
    职责：返回标准化后的消息对象列表
    1. 标准历史消息(用户角色的消息标准成HumanMessage 非用户角色的消息标准为AIMessage)
    2. 标准轮次的消息
    """

    # 1. 构建历史消息
    history: list[dict[str, Any]] = _build_history_messages(payload.history)

    # 2. 格式化历史消息为标准的LangChain消息对象
    final_messages: list[BaseMessage] = [
        HumanMessage(content=_format_message(message))
        if message['role'] == "USER" else
        AIMessage(content=_format_message(message))
        for message in history
    ]

    # 3. 构建当前轮次的消息
    message_content = _build_current_messages(payload.message)
    final_messages.append(HumanMessage(content=message_content))

    # 4. 标准后统一返回
    return  final_messages


def _build_history_messages(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """

    职责：对历史消息做裁剪 三级策略裁剪
    策略1：最近的指定条数裁剪 (30条)
    策略2：消息内容的字符数裁剪 (12000字符数)
    策略3：对经过策略2留下的候选历史消息在根据消息角色裁剪【从第一条消息角色是用户的开始留】
    """
    settings = get_settings()

    # 1. 策略一：获取指定条数的历史消息(最多留下最近的30条)
    candidate_history_messages = history[-settings.history_message_limit:]

    # 2. 反转之后计算消息内容的字符数
    total_usage = 0
    messages = []
    for message in reversed(candidate_history_messages):
        # a) 格式化单条消息
        message_content = _format_message(message)

        # b) 获取单条消息内容的长度
        message_len = len(message_content)

        # c) 已经达到消息字符数上限,当前消息不会留下
        if message_len + total_usage > settings.history_character_budget:
            break

        # d) 没有达到消息字符数上限,将当前消息收集起来以及更新计数器的值
        messages.append(message)
        total_usage += message_len

    # 3. 反转
    messages.reverse()

    # 4. next() 列表是可迭代对象，生成器是一个迭代器
    user_role_index = next((index for index, message in enumerate(messages) if message['role'] == "USER"), None)

    # 5. 返回
    return messages[user_role_index:] if user_role_index is not None else messages  # user_role_index为None 可以选择给或者不给


def _format_message(message: dict[str, Any]) -> str:
    """
    职责：格式化单条消息对象的内容字符串部分
    注意：单条消息考虑消息类型（USER角色消息：类型text or object）
    """

    # 1. 消息类型是文本
    if message['type'] == "text":
        return message['content'].get('text')

    # 2. 消息类型是对象(卡片：订单类型 or  商品类型)
    object_message_content = message['content']

    return "该消息类型是一个对象结构:\n" + json.dumps(object_message_content, indent=2, ensure_ascii=False)



def _build_current_messages(turn_messages:list[dict[str,Any]])->str:
    """
    职责：处理当前轮次的所有消息内容为一个大字符串
    """
    # 1. 收集当前轮次所有消息的内容
    messages_content=[_format_message(message) for  message  in  turn_messages]


    # 2. 当前轮次的消息只有一条
    if  len(messages_content)==1:
        return  messages_content[0]

    # 3. 当前轮次得消息有多条  1.xxx 2.yyy 3.zzz

    items= "\n".join([f"{index}. {content}" for index,content in enumerate(messages_content,start=1)])

    return  "当前用户发送了多条消息,请您作为一个整体来理解\n\n"+ items











