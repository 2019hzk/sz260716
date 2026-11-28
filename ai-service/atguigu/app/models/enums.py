from enum import StrEnum


class AgentTraceStatus(StrEnum):
    """
    Agent运行的状态

    """

    RUNNING = "RUNNING"  # Agent正在运行
    COMPLETED = "COMPLETED"  # Agent运行完毕(成功运行完)
    FAILED = "FAILED"  # Agent运行期间出现问题
