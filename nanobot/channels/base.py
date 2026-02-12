"""聊天平台的基础渠道接口。

此模块定义了所有聊天渠道实现必须继承的抽象基类。
每个渠道（Telegram、Discord等）都应该实现此接口以与nanobot消息总线集成。
"""

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus


class BaseChannel(ABC):
    """
    聊天渠道实现的抽象基类。
    
    每个渠道（Telegram、Discord等）都应该实现此接口以与nanobot消息总线集成。
    实现类需要：
    - 连接到聊天平台
    - 监听入站消息并转发到消息总线
    - 从消息总线接收出站消息并发送到平台
    - 实现权限检查
    """
    
    name: str = "base"  # 渠道名称
    
    def __init__(self, config: Any, bus: MessageBus):
        """
        初始化渠道。
        
        Args:
            config: 渠道特定的配置对象
            bus: 用于通信的消息总线
        """
        self.config = config
        self.bus = bus
        self._running = False  # 运行状态标志
    
    @abstractmethod
    async def start(self) -> None:
        """
        启动渠道并开始监听消息。
        
        这应该是一个长期运行的异步任务，执行以下操作：
        1. 连接到聊天平台
        2. 监听入站消息
        3. 通过_handle_message()将消息转发到总线
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """
        停止渠道并清理资源。
        
        应该断开与聊天平台的连接，清理所有资源。
        """
        pass
    
    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """
        通过此渠道发送消息。
        
        Args:
            msg: 要发送的消息
        """
        pass
    
    def is_allowed(self, sender_id: str) -> bool:
        """
        检查发送者是否被允许使用此机器人。
        
        如果配置了allow_from列表，则只允许列表中的用户。
        如果列表为空，则允许所有人。
        支持复合ID（使用"|"分隔），会检查所有部分。
        
        Args:
            sender_id: 发送者的标识符
        
        Returns:
            如果允许返回True，否则返回False
        """
        allow_list = getattr(self.config, "allow_from", [])
        
        # 如果没有允许列表，允许所有人
        if not allow_list:
            return True
        
        sender_str = str(sender_id)
        if sender_str in allow_list:
            return True
        # 支持复合ID（例如"user_id|group_id"）
        if "|" in sender_str:
            for part in sender_str.split("|"):
                if part and part in allow_list:
                    return True
        return False
    
    async def _handle_message(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        media: list[str] | None = None,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """
        处理来自聊天平台的入站消息。
        
        此方法检查权限并将消息转发到消息总线。
        
        Args:
            sender_id: 发送者的标识符
            chat_id: 聊天/频道标识符
            content: 消息文本内容
            media: 可选的媒体URL列表
            metadata: 可选的渠道特定元数据
        """
        if not self.is_allowed(sender_id):
            logger.warning(
                f"Access denied for sender {sender_id} on channel {self.name}. "
                f"Add them to allowFrom list in config to grant access."
            )
            return
        
        msg = InboundMessage(
            channel=self.name,
            sender_id=str(sender_id),
            chat_id=str(chat_id),
            content=content,
            media=media or [],
            metadata=metadata or {}
        )
        
        await self.bus.publish_inbound(msg)
    
    @property
    def is_running(self) -> bool:
        """
        检查渠道是否正在运行。
        
        Returns:
            如果渠道正在运行返回True，否则返回False
        """
        return self._running
