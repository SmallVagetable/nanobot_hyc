"""消息总线的事件类型。

此模块定义了消息总线使用的数据结构：
- InboundMessage: 从聊天渠道接收的消息
- OutboundMessage: 要发送到聊天渠道的消息
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class InboundMessage:
    """
    从聊天渠道接收的消息。
    
    包含消息的所有相关信息，包括渠道、发送者、内容等。
    用于将来自不同渠道的消息统一格式化为内部消息格式。
    """
    
    channel: str  # 渠道名称：telegram, discord, slack, whatsapp等
    sender_id: str  # 用户标识符
    chat_id: str  # 聊天/频道标识符
    content: str  # 消息文本内容
    timestamp: datetime = field(default_factory=datetime.now)  # 消息时间戳
    media: list[str] = field(default_factory=list)  # 媒体文件URL列表
    metadata: dict[str, Any] = field(default_factory=dict)  # 渠道特定的元数据
    
    @property
    def session_key(self) -> str:
        """
        获取会话的唯一标识键。
        
        会话键由渠道和聊天ID组成，格式为"channel:chat_id"。
        用于在会话管理器中标识和管理不同的对话会话。
        
        Returns:
            会话键字符串
        """
        return f"{self.channel}:{self.chat_id}"


@dataclass
class OutboundMessage:
    """
    要发送到聊天渠道的消息。
    
    包含要发送的消息内容、目标渠道、接收者等信息。
    用于将智能体的响应统一格式化为可发送的消息格式。
    """
    
    channel: str  # 目标渠道名称
    chat_id: str  # 目标聊天/用户ID
    content: str  # 消息内容
    reply_to: str | None = None  # 要回复的消息ID（可选）
    media: list[str] = field(default_factory=list)  # 媒体文件列表（可选）
    metadata: dict[str, Any] = field(default_factory=dict)  # 渠道特定的元数据


