"""消息总线模块，用于解耦渠道-智能体通信。

此模块实现了消息总线，用于在聊天渠道和智能体核心之间传递消息。
通过消息队列实现了解耦，使得渠道和智能体可以独立运行和扩展。
"""

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus

__all__ = ["MessageBus", "InboundMessage", "OutboundMessage"]
