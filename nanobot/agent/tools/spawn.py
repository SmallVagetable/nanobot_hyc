"""子智能体生成工具，用于创建后台子智能体。

此模块提供了生成子智能体的工具，允许主智能体创建轻量级的
子智能体来执行后台任务。子智能体异步运行，完成后会通知主智能体。
"""

from typing import Any, TYPE_CHECKING

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.agent.subagent import SubagentManager


class SpawnTool(Tool):
    """
    生成子智能体执行后台任务的工具。
    
    用于创建子智能体来处理复杂或耗时的任务。子智能体会：
    - 异步运行，不阻塞主智能体
    - 拥有独立的上下文和聚焦的系统提示词
    - 任务完成后通过消息总线通知主智能体
    
    适用于可以独立运行的复杂任务，如数据分析、文件处理等。
    """
    
    def __init__(self, manager: "SubagentManager"):
        """
        初始化子智能体生成工具。
        
        Args:
            manager: 子智能体管理器实例
        """
        self._manager = manager
        self._origin_channel = "cli"  # 原始渠道，用于通知返回
        self._origin_chat_id = "direct"  # 原始聊天ID，用于通知返回
    
    def set_context(self, channel: str, chat_id: str) -> None:
        """
        设置子智能体通知的原始上下文。
        
        当子智能体完成任务后，会使用此上下文将结果通知回主智能体。
        
        Args:
            channel: 原始渠道
            chat_id: 原始聊天ID
        """
        self._origin_channel = channel
        self._origin_chat_id = chat_id
    
    @property
    def name(self) -> str:
        return "spawn"
    
    @property
    def description(self) -> str:
        return (
            "Spawn a subagent to handle a task in the background. "
            "Use this for complex or time-consuming tasks that can run independently. "
            "The subagent will complete the task and report back when done."
        )
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task for the subagent to complete",
                },
                "label": {
                    "type": "string",
                    "description": "Optional short label for the task (for display)",
                },
            },
            "required": ["task"],
        }
    
    async def execute(self, task: str, label: str | None = None, **kwargs: Any) -> str:
        """
        生成子智能体执行指定任务。
        
        Args:
            task: 子智能体要完成的任务描述
            label: 可选的任务标签（用于显示）
        
        Returns:
            状态消息，表示子智能体已启动
        """
        return await self._manager.spawn(
            task=task,
            label=label,
            origin_channel=self._origin_channel,
            origin_chat_id=self._origin_chat_id,
        )
