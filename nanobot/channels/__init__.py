"""聊天渠道模块，采用插件架构。

此模块提供了聊天渠道的基础接口和管理器，支持多种聊天平台
（Telegram、WhatsApp、Discord等）的集成。
"""

from nanobot.channels.base import BaseChannel
from nanobot.channels.manager import ChannelManager

__all__ = ["BaseChannel", "ChannelManager"]
