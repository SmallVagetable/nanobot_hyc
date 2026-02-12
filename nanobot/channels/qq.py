"""使用botpy SDK实现的QQ渠道。

此模块实现了QQ聊天渠道，使用botpy SDK通过WebSocket连接。
支持私聊消息的接收和发送。
"""

import asyncio
from collections import deque
from typing import TYPE_CHECKING

from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import QQConfig

try:
    import botpy
    from botpy.message import C2CMessage

    QQ_AVAILABLE = True
except ImportError:
    QQ_AVAILABLE = False
    botpy = None
    C2CMessage = None

if TYPE_CHECKING:
    from botpy.message import C2CMessage


def _make_bot_class(channel: "QQChannel") -> "type[botpy.Client]":
    """
    创建绑定到给定渠道的botpy Client子类。
    
    Args:
        channel: QQ渠道实例
    
    Returns:
        botpy Client子类
    """
    intents = botpy.Intents(public_messages=True, direct_message=True)

    class _Bot(botpy.Client):
        def __init__(self):
            super().__init__(intents=intents)

        async def on_ready(self):
            logger.info(f"QQ bot ready: {self.robot.name}")

        async def on_c2c_message_create(self, message: "C2CMessage"):
            await channel._on_message(message)

        async def on_direct_message_create(self, message):
            await channel._on_message(message)

    return _Bot


class QQChannel(BaseChannel):
    """
    使用botpy SDK和WebSocket连接的QQ渠道。
    
    通过botpy SDK连接QQ开放平台，支持私聊消息的接收和发送。
    支持自动重连，当连接断开时会自动尝试重新连接。
    """

    name = "qq"

    def __init__(self, config: QQConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: QQConfig = config
        self._client: "botpy.Client | None" = None
        self._processed_ids: deque = deque(maxlen=1000)
        self._bot_task: asyncio.Task | None = None

    async def start(self) -> None:
        """
        启动QQ机器人。
        
        初始化botpy客户端并开始连接，支持自动重连。
        """
        if not QQ_AVAILABLE:
            logger.error("QQ SDK not installed. Run: pip install qq-botpy")
            return

        if not self.config.app_id or not self.config.secret:
            logger.error("QQ app_id and secret not configured")
            return

        self._running = True
        BotClass = _make_bot_class(self)
        self._client = BotClass()

        self._bot_task = asyncio.create_task(self._run_bot())
        logger.info("QQ bot started (C2C private message)")

    async def _run_bot(self) -> None:
        """
        运行机器人连接，支持自动重连。
        
        持续运行机器人连接，如果连接断开会自动尝试重新连接。
        """
        while self._running:
            try:
                await self._client.start(appid=self.config.app_id, secret=self.config.secret)
            except Exception as e:
                logger.warning(f"QQ bot error: {e}")
            if self._running:
                logger.info("Reconnecting QQ bot in 5 seconds...")
                await asyncio.sleep(5)

    async def stop(self) -> None:
        """
        停止QQ机器人。
        
        取消机器人任务并清理资源。
        """
        self._running = False
        if self._bot_task:
            self._bot_task.cancel()
            try:
                await self._bot_task
            except asyncio.CancelledError:
                pass
        logger.info("QQ bot stopped")

    async def send(self, msg: OutboundMessage) -> None:
        """
        通过QQ发送消息。
        
        Args:
            msg: 要发送的出站消息
        """
        if not self._client:
            logger.warning("QQ client not initialized")
            return
        try:
            await self._client.api.post_c2c_message(
                openid=msg.chat_id,
                msg_type=0,
                content=msg.content,
            )
        except Exception as e:
            logger.error(f"Error sending QQ message: {e}")

    async def _on_message(self, data: "C2CMessage") -> None:
        """
        处理来自QQ的入站消息。

        使用消息ID进行去重，然后将消息内容转发到消息总线。

        Args:
            data: C2C消息对象
        """
        try:
            # 按消息ID去重
            if data.id in self._processed_ids:
                return
            self._processed_ids.append(data.id)

            author = data.author
            user_id = str(getattr(author, 'id', None) or getattr(author, 'user_openid', 'unknown'))
            content = (data.content or "").strip()
            if not content:
                return

            await self._handle_message(
                sender_id=user_id,
                chat_id=user_id,
                content=content,
                metadata={"message_id": data.id},
            )
        except Exception as e:
            logger.error(f"Error handling QQ message: {e}")
