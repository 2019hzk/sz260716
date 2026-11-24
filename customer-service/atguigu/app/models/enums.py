from enum import StrEnum, Enum


class ConversationMode(StrEnum):
    """
    会话模式：4种
    """
    AI = "AI"
    QUEUED = "QUEUED"   # 等待人工
    HUMAN = "HUMAN"     # 人工接收工单
    CLOSED = "CLOSED"   # 主动因为超时时间到了，修改【创建会话的时候。messages/history接口】


class MessageRole(StrEnum):
    """
    消息角色：3种
    """
    USER = "USER"
    AI = "AI"
    HUMAN = "HUMAN"


class TurnStatus(StrEnum):
    """
    轮次状态：5种
    """
    COLLECTING = "COLLECTING"  # 初始态
    RUNNING = "RUNNING"  # 中间态
    COMPLETED = "COMPLETED"  # 最终态(在推理期间，用户未插话)
    SUPERSEDED = "SUPERSEDED"  # 最终态(在推理期间，用户插话)
    FAILED = "FAILED"  # 最终态(AI-Service达到最大的重试次数)


class HandoffStatus(StrEnum):
    """
    工单状态
    """

    WAITING = "WAITING"
    ACTIVE = "ACTIVE"
    RESOLVE = "RESOLVE"
