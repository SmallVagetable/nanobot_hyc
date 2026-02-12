"""渠道管理器，用于协调聊天渠道。

此模块实现了渠道管理器，负责：
- 根据配置初始化启用的渠道（Telegram、WhatsApp等）
- 启动和停止渠道
- 路由出站消息到相应的渠道
"""

from __future__ import annotations

import asyncio
from typing import Any, TYPE_CHECKING

from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import Config

if TYPE_CHECKING:
    from nanobot.session.manager import SessionManager


class ChannelManager:
    """
    管理聊天渠道并协调消息路由。
    
    职责：
    - 初始化启用的渠道（Telegram、WhatsApp等）
    - 启动/停止渠道
    - 路由出站消息到相应的渠道
    
    渠道管理器从消息总线接收出站消息，并根据消息的渠道字段
    将消息路由到相应的渠道实现。
    """
    
    def __init__(self, config: Config, bus: MessageBus, session_manager: "SessionManager | None" = None):
        """
        初始化渠道管理器。
        
        Args:
            config: 配置对象
            bus: 消息总线
            session_manager: 会话管理器（可选）
        """
        self.config = config
        self.bus = bus
        self.session_manager = session_manager
        self.channels: dict[str, BaseChannel] = {}  # 已初始化的渠道字典
        self._dispatch_task: asyncio.Task | None = None  # 消息分发任务
        
        self._init_channels()
    
    def _init_channels(self) -> None:
        """
        根据配置初始化渠道。
        
        检查配置中启用的渠道，并创建相应的渠道实例。
        如果某个渠道的依赖未安装，会记录警告但不会中断初始化。
        """
        
        # Telegram channel
        if self.config.channels.telegram.enabled:
            try:
                from nanobot.channels.telegram import TelegramChannel
                self.channels["telegram"] = TelegramChannel(
                    self.config.channels.telegram,
                    self.bus,
                    groq_api_key=self.config.providers.groq.api_key,
                    session_manager=self.session_manager,
                )
                logger.info("Telegram channel enabled")
            except ImportError as e:
                logger.warning(f"Telegram channel not available: {e}")
        
        # WhatsApp channel
        if self.config.channels.whatsapp.enabled:
            try:
                from nanobot.channels.whatsapp import WhatsAppChannel
                self.channels["whatsapp"] = WhatsAppChannel(
                    self.config.channels.whatsapp, self.bus
                )
                logger.info("WhatsApp channel enabled")
            except ImportError as e:
                logger.warning(f"WhatsApp channel not available: {e}")

        # Discord channel
        if self.config.channels.discord.enabled:
            try:
                from nanobot.channels.discord import DiscordChannel
                self.channels["discord"] = DiscordChannel(
                    self.config.channels.discord, self.bus
                )
                logger.info("Discord channel enabled")
            except ImportError as e:
                logger.warning(f"Discord channel not available: {e}")
        
        # Feishu channel
        if self.config.channels.feishu.enabled:
            try:
                from nanobot.channels.feishu import FeishuChannel
                self.channels["feishu"] = FeishuChannel(
                    self.config.channels.feishu, self.bus
                )
                logger.info("Feishu channel enabled")
            except ImportError as e:
                logger.warning(f"Feishu channel not available: {e}")

        # Mochat channel
        if self.config.channels.mochat.enabled:
            try:
                from nanobot.channels.mochat import MochatChannel

                self.channels["mochat"] = MochatChannel(
                    self.config.channels.mochat, self.bus
                )
                logger.info("Mochat channel enabled")
            except ImportError as e:
                logger.warning(f"Mochat channel not available: {e}")

        # DingTalk channel
        if self.config.channels.dingtalk.enabled:
            try:
                from nanobot.channels.dingtalk import DingTalkChannel
                self.channels["dingtalk"] = DingTalkChannel(
                    self.config.channels.dingtalk, self.bus
                )
                logger.info("DingTalk channel enabled")
            except ImportError as e:
                logger.warning(f"DingTalk channel not available: {e}")

        # Email channel
        if self.config.channels.email.enabled:
            try:
                from nanobot.channels.email import EmailChannel
                self.channels["email"] = EmailChannel(
                    self.config.channels.email, self.bus
                )
                logger.info("Email channel enabled")
            except ImportError as e:
                logger.warning(f"Email channel not available: {e}")

        # Slack channel
        if self.config.channels.slack.enabled:
            try:
                from nanobot.channels.slack import SlackChannel
                self.channels["slack"] = SlackChannel(
                    self.config.channels.slack, self.bus
                )
                logger.info("Slack channel enabled")
            except ImportError as e:
                logger.warning(f"Slack channel not available: {e}")

        # QQ channel
        if self.config.channels.qq.enabled:
            try:
                from nanobot.channels.qq import QQChannel
                self.channels["qq"] = QQChannel(
                    self.config.channels.qq,
                    self.bus,
                )
                logger.info("QQ channel enabled")
            except ImportError as e:
                logger.warning(f"QQ channel not available: {e}")
    
    async def _start_channel(self, name: str, channel: BaseChannel) -> None:
        """
        启动一个渠道并记录任何异常。
        
        Args:
            name: 渠道名称
            channel: 渠道实例
        """
        try:
            await channel.start()
        except Exception as e:
            logger.error(f"Failed to start channel {name}: {e}")

    async def start_all(self) -> None:
        """
        启动所有渠道和出站消息分发器。
        
        启动所有已初始化的渠道，并启动出站消息分发器。
        所有任务会并发运行，直到被停止。
        """
        if not self.channels:
            logger.warning("No channels enabled")
            return
        
        # 启动出站消息分发器
        self._dispatch_task = asyncio.create_task(self._dispatch_outbound())
        
        # 启动所有渠道
        tasks = []
        for name, channel in self.channels.items():
            logger.info(f"Starting {name} channel...")
            tasks.append(asyncio.create_task(self._start_channel(name, channel)))
        
        # 等待所有任务完成（它们应该永远运行）
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop_all(self) -> None:
        """
        停止所有渠道和分发器。
        
        优雅地停止所有正在运行的渠道和消息分发器。
        """
        logger.info("Stopping all channels...")
        
        # 停止分发器
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
        
        # 停止所有渠道
        for name, channel in self.channels.items():
            try:
                await channel.stop()
                logger.info(f"Stopped {name} channel")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
    
    async def _dispatch_outbound(self) -> None:
        """
        将出站消息分发到相应的渠道。
        
        从消息总线消费出站消息，并根据消息的渠道字段
        将消息路由到相应的渠道实现。
        """
        logger.info("Outbound dispatcher started")
        
        while True:
            try:
                msg = await asyncio.wait_for(
                    self.bus.consume_outbound(),
                    timeout=1.0
                )
                
                channel = self.channels.get(msg.channel)
                if channel:
                    try:
                        await channel.send(msg)
                    except Exception as e:
                        logger.error(f"Error sending to {msg.channel}: {e}")
                else:
                    logger.warning(f"Unknown channel: {msg.channel}")
                    
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
    
    def get_channel(self, name: str) -> BaseChannel | None:
        """Get a channel by name."""
        return self.channels.get(name)
    
    def get_status(self) -> dict[str, Any]:
        """Get status of all channels."""
        return {
            name: {
                "enabled": True,
                "running": channel.is_running
            }
            for name, channel in self.channels.items()
        }
    
    @property
    def enabled_channels(self) -> list[str]:
        """Get list of enabled channel names."""
        return list(self.channels.keys())
