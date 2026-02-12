"""定时任务类型定义。

此模块定义了定时任务系统的所有数据类型，包括：
- CronSchedule: 任务调度定义
- CronPayload: 任务执行内容
- CronJobState: 任务运行时状态
- CronJob: 定时任务
- CronStore: 任务存储
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class CronSchedule:
    """
    定时任务的调度定义。
    
    支持三种调度类型：
    - "at": 在指定时间点执行一次
    - "every": 每隔指定时间间隔执行
    - "cron": 使用cron表达式定义复杂调度
    """
    kind: Literal["at", "every", "cron"]  # 调度类型
    at_ms: int | None = None  # 对于"at"类型：时间戳（毫秒）
    every_ms: int | None = None  # 对于"every"类型：时间间隔（毫秒）
    expr: str | None = None  # 对于"cron"类型：cron表达式（例如"0 9 * * *"）
    tz: str | None = None  # cron表达式使用的时区


@dataclass
class CronPayload:
    """
    任务执行时的内容定义。
    
    定义当任务触发时要执行的操作，通常是发送消息给智能体。
    """
    kind: Literal["system_event", "agent_turn"] = "agent_turn"  # 任务类型
    message: str = ""  # 要发送给智能体的消息
    deliver: bool = False  # 是否将响应发送到渠道
    channel: str | None = None  # 目标渠道，例如"whatsapp"
    to: str | None = None  # 目标接收者，例如电话号码


@dataclass
class CronJobState:
    """
    任务的运行时状态。
    
    记录任务的执行状态，包括下次运行时间、上次运行时间、执行结果等。
    """
    next_run_at_ms: int | None = None  # 下次运行时间（毫秒）
    last_run_at_ms: int | None = None  # 上次运行时间（毫秒）
    last_status: Literal["ok", "error", "skipped"] | None = None  # 上次执行状态
    last_error: str | None = None  # 上次执行错误信息（如果有）


@dataclass
class CronJob:
    """
    定时任务。
    
    包含任务的完整定义，包括调度、执行内容、状态等。
    """
    id: str  # 任务ID
    name: str  # 任务名称
    enabled: bool = True  # 是否启用
    schedule: CronSchedule = field(default_factory=lambda: CronSchedule(kind="every"))  # 调度定义
    payload: CronPayload = field(default_factory=CronPayload)  # 执行内容
    state: CronJobState = field(default_factory=CronJobState)  # 运行时状态
    created_at_ms: int = 0  # 创建时间（毫秒）
    updated_at_ms: int = 0  # 更新时间（毫秒）
    delete_after_run: bool = False  # 执行后是否删除（用于一次性任务）


@dataclass
class CronStore:
    """
    定时任务的持久化存储。
    
    包含所有定时任务的列表和存储版本信息。
    """
    version: int = 1  # 存储格式版本
    jobs: list[CronJob] = field(default_factory=list)  # 任务列表
