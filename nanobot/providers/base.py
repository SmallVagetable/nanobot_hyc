"""LLM提供者的基础接口。

此模块定义了LLM提供者的抽象基类和数据结构。
所有LLM提供者实现都必须继承自LLMProvider类，并实现其抽象方法。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCallRequest:
    """
    LLM发出的工具调用请求。
    
    包含工具调用的所有信息，包括工具ID、名称和参数。
    """
    id: str  # 工具调用ID
    name: str  # 工具名称
    arguments: dict[str, Any]  # 工具参数


@dataclass
class LLMResponse:
    """
    LLM提供者的响应。
    
    包含LLM的响应内容、工具调用、完成原因等信息。
    """
    content: str | None  # 响应文本内容
    tool_calls: list[ToolCallRequest] = field(default_factory=list)  # 工具调用列表
    finish_reason: str = "stop"  # 完成原因（stop、length、tool_calls等）
    usage: dict[str, int] = field(default_factory=dict)  # Token使用统计
    reasoning_content: str | None = None  # 推理内容（用于支持思考过程的模型，如Kimi、DeepSeek-R1等）
    
    @property
    def has_tool_calls(self) -> bool:
        """
        检查响应是否包含工具调用。
        
        Returns:
            如果包含工具调用返回True，否则返回False
        """
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    """
    LLM提供者的抽象基类。
    
    所有LLM提供者实现都必须继承此类并实现抽象方法。
    实现类应该处理每个提供者API的特定细节，同时保持一致的接口。
    
    这允许系统支持多种LLM提供者（OpenAI、Anthropic、DeepSeek等），
    而无需修改核心代码。
    """
    
    def __init__(self, api_key: str | None = None, api_base: str | None = None):
        """
        初始化LLM提供者。
        
        Args:
            api_key: API密钥
            api_base: API基础URL（可选）
        """
        self.api_key = api_key
        self.api_base = api_base
    
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        发送聊天完成请求。
        
        Args:
            messages: 消息列表，每个消息包含'role'和'content'字段
            tools: 可选的工具定义列表
            model: 模型标识符（提供者特定）
            max_tokens: 响应的最大token数
            temperature: 采样温度
        
        Returns:
            包含内容和/或工具调用的LLMResponse
        """
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """
        获取此提供者的默认模型。
        
        Returns:
            默认模型名称
        """
        pass
