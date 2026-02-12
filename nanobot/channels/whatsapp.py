"""使用Node.js桥接实现的WhatsApp渠道。

此模块实现了WhatsApp聊天渠道，通过Node.js桥接服务连接。
桥接使用@whiskeysockets/baileys处理WhatsApp Web协议。
Python和Node.js之间通过WebSocket通信。
"""

import asyncio
import json
from typing import Any

from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import WhatsAppConfig


class WhatsAppChannel(BaseChannel):
    """
    连接到Node.js桥接的WhatsApp渠道。
    
    桥接使用@whiskeysockets/baileys处理WhatsApp Web协议。
    Python和Node.js之间通过WebSocket进行通信。
    
    支持自动重连，当连接断开时会自动尝试重新连接。
    """
    
    name = "whatsapp"
    
    def __init__(self, config: WhatsAppConfig, bus: MessageBus):
        """
        初始化WhatsApp渠道。
        
        Args:
            config: WhatsApp配置
            bus: 消息总线
        """
        super().__init__(config, bus)
        self.config: WhatsAppConfig = config
        self._ws = None  # WebSocket连接
        self._connected = False  # 连接状态
    
    async def start(self) -> None:
        """
        通过连接到桥接启动WhatsApp渠道。
        
        连接到Node.js桥接服务，监听消息并自动重连。
        """
        import websockets
        
        bridge_url = self.config.bridge_url
        
        logger.info(f"Connecting to WhatsApp bridge at {bridge_url}...")
        
        self._running = True
        
        while self._running:
            try:
                async with websockets.connect(bridge_url) as ws:
                    self._ws = ws
                    self._connected = True
                    logger.info("Connected to WhatsApp bridge")
                    
                    # 监听消息
                    async for message in ws:
                        try:
                            await self._handle_bridge_message(message)
                        except Exception as e:
                            logger.error(f"Error handling bridge message: {e}")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._connected = False
                self._ws = None
                logger.warning(f"WhatsApp bridge connection error: {e}")
                
                if self._running:
                    logger.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)
    
    async def stop(self) -> None:
        """
        停止WhatsApp渠道。
        
        关闭WebSocket连接并清理资源。
        """
        self._running = False
        self._connected = False
        
        if self._ws:
            await self._ws.close()
            self._ws = None
    
    async def send(self, msg: OutboundMessage) -> None:
        """
        通过WhatsApp发送消息。
        
        Args:
            msg: 要发送的出站消息
        """
        if not self._ws or not self._connected:
            logger.warning("WhatsApp bridge not connected")
            return
        
        try:
            payload = {
                "type": "send",
                "to": msg.chat_id,
                "text": msg.content
            }
            await self._ws.send(json.dumps(payload))
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
    
    async def _handle_bridge_message(self, raw: str) -> None:
        """
        处理来自桥接的消息。
        
        解析桥接发送的JSON消息，根据消息类型进行处理：
        - message: 来自WhatsApp的消息
        - status: 连接状态更新
        - qr: QR码认证
        - error: 错误信息
        
        Args:
            raw: 原始JSON字符串
        """
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from bridge: {raw[:100]}")
            return
        
        msg_type = data.get("type")
        
        if msg_type == "message":
            # 来自WhatsApp的入站消息
            # WhatsApp已弃用：旧的电话号码格式通常是 <phone>@s.whatsapp.net
            pn = data.get("pn", "")
            # 新的LID格式通常是：
            sender = data.get("sender", "")
            content = data.get("content", "")
            
            # 提取电话号码或LID作为chat_id
            user_id = pn if pn else sender
            sender_id = user_id.split("@")[0] if "@" in user_id else user_id
            logger.info(f"Sender {sender}")
            
            # 如果是语音消息，处理语音转文字
            if content == "[Voice Message]":
                logger.info(f"Voice message received from {sender_id}, but direct download from bridge is not yet supported.")
                content = "[Voice Message: Transcription not available for WhatsApp yet]"
            
            await self._handle_message(
                sender_id=sender_id,
                chat_id=sender,  # 使用完整LID用于回复
                content=content,
                metadata={
                    "message_id": data.get("id"),
                    "timestamp": data.get("timestamp"),
                    "is_group": data.get("isGroup", False)
                }
            )
        
        elif msg_type == "status":
            # 连接状态更新
            status = data.get("status")
            logger.info(f"WhatsApp status: {status}")
            
            if status == "connected":
                self._connected = True
            elif status == "disconnected":
                self._connected = False
        
        elif msg_type == "qr":
            # QR码认证
            logger.info("Scan QR code in the bridge terminal to connect WhatsApp")
        
        elif msg_type == "error":
            logger.error(f"WhatsApp bridge error: {data.get('error')}")
