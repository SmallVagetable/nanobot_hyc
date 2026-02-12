"""定时任务工具，用于调度提醒和任务。

此模块提供了定时任务调度工具，允许智能体创建定时任务：
- 周期性任务（每隔N秒执行）
- Cron表达式任务（按时间表执行）
- 任务列表查看
- 任务删除

任务执行后可以将结果发送到指定渠道。
"""

from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule


class CronTool(Tool):
    """
    调度提醒和周期性任务的工具。
    
    支持三种操作：
    - add: 添加新的定时任务
    - list: 列出所有定时任务
    - remove: 删除指定的定时任务
    
    任务可以配置为周期性执行（每隔N秒）或按Cron表达式执行。
    任务执行后可以将结果发送到当前会话的渠道。
    """
    
    def __init__(self, cron_service: CronService):
        """
        初始化定时任务工具。
        
        Args:
            cron_service: 定时任务服务实例
        """
        self._cron = cron_service
        self._channel = ""  # 当前会话渠道
        self._chat_id = ""  # 当前会话聊天ID
    
    def set_context(self, channel: str, chat_id: str) -> None:
        """
        设置当前会话上下文，用于任务结果投递。
        
        Args:
            channel: 当前会话渠道
            chat_id: 当前会话聊天ID
        """
        self._channel = channel
        self._chat_id = chat_id
    
    @property
    def name(self) -> str:
        return "cron"
    
    @property
    def description(self) -> str:
        return "Schedule reminders and recurring tasks. Actions: add, list, remove."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "list", "remove"],
                    "description": "Action to perform"
                },
                "message": {
                    "type": "string",
                    "description": "Reminder message (for add)"
                },
                "every_seconds": {
                    "type": "integer",
                    "description": "Interval in seconds (for recurring tasks)"
                },
                "cron_expr": {
                    "type": "string",
                    "description": "Cron expression like '0 9 * * *' (for scheduled tasks)"
                },
                "job_id": {
                    "type": "string",
                    "description": "Job ID (for remove)"
                }
            },
            "required": ["action"]
        }
    
    async def execute(
        self,
        action: str,
        message: str = "",
        every_seconds: int | None = None,
        cron_expr: str | None = None,
        job_id: str | None = None,
        **kwargs: Any
    ) -> str:
        if action == "add":
            return self._add_job(message, every_seconds, cron_expr)
        elif action == "list":
            return self._list_jobs()
        elif action == "remove":
            return self._remove_job(job_id)
        return f"Unknown action: {action}"
    
    def _add_job(self, message: str, every_seconds: int | None, cron_expr: str | None) -> str:
        """
        添加新的定时任务。
        
        Args:
            message: 任务消息（要发送给智能体的内容）
            every_seconds: 周期性任务的间隔（秒）
            cron_expr: Cron表达式（用于按时间表执行）
        
        Returns:
            任务创建结果消息
        """
        if not message:
            return "Error: message is required for add"
        if not self._channel or not self._chat_id:
            return "Error: no session context (channel/chat_id)"
        
        # 构建调度定义
        if every_seconds:
            schedule = CronSchedule(kind="every", every_ms=every_seconds * 1000)
        elif cron_expr:
            schedule = CronSchedule(kind="cron", expr=cron_expr)
        else:
            return "Error: either every_seconds or cron_expr is required"
        
        job = self._cron.add_job(
            name=message[:30],
            schedule=schedule,
            message=message,
            deliver=True,
            channel=self._channel,
            to=self._chat_id,
        )
        return f"Created job '{job.name}' (id: {job.id})"
    
    def _list_jobs(self) -> str:
        """
        列出所有定时任务。
        
        Returns:
            任务列表字符串
        """
        jobs = self._cron.list_jobs()
        if not jobs:
            return "No scheduled jobs."
        lines = [f"- {j.name} (id: {j.id}, {j.schedule.kind})" for j in jobs]
        return "Scheduled jobs:\n" + "\n".join(lines)
    
    def _remove_job(self, job_id: str | None) -> str:
        """
        删除指定的定时任务。
        
        Args:
            job_id: 要删除的任务ID
        
        Returns:
            删除结果消息
        """
        if not job_id:
            return "Error: job_id is required for remove"
        if self._cron.remove_job(job_id):
            return f"Removed job {job_id}"
        return f"Job {job_id} not found"
