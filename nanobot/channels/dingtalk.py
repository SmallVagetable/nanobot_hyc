"""使用Stream模式实现的钉钉渠道。

此模块实现了钉钉聊天渠道，使用Stream模式通过WebSocket接收事件。
使用钉钉Stream SDK处理消息接收，使用HTTP API发送消息。
"""

import asyncio
import json
import time
from typing import Any

from loguru import logger
import httpx

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import DingTalkConfig

try:
    from dingtalk_stream import (
        DingTalkStreamClient,
        Credential,
        CallbackHandler,
        CallbackMessage,
        AckMessage,
    )
    from dingtalk_stream.chatbot import ChatbotMessage

    DINGTALK_AVAILABLE = True
except ImportError:
    DINGTALK_AVAILABLE = False
    # 回退，避免模块级别的类定义崩溃
    CallbackHandler = object  # type: ignore[assignment,misc]
    CallbackMessage = None  # type: ignore[assignment,misc]
    AckMessage = None  # type: ignore[assignment,misc]
    ChatbotMessage = None  # type: ignore[assignment,misc]


class NanobotDingTalkHandler(CallbackHandler):
    """
    标准的钉钉Stream SDK回调处理器。
    
    解析入站消息并将其转发到Nanobot渠道。
    """

    def __init__(self, channel: "DingTalkChannel"):
        """
        初始化处理器。
        
        Args:
            channel: 钉钉渠道实例
        """
        super().__init__()
        self.channel = channel

    async def process(self, message: CallbackMessage):
        """
        处理入站的流消息。
        
        Args:
            message: 回调消息对象
        
        Returns:
            确认消息状态和响应
        """
        try:
            # Parse using SDK's ChatbotMessage for robust handling
            chatbot_msg = ChatbotMessage.from_dict(message.data)

            # Extract text content; fall back to raw dict if SDK object is empty
            content = ""
            if chatbot_msg.text:
                content = chatbot_msg.text.content.strip()
            if not content:
                content = message.data.get("text", {}).get("content", "").strip()

            if not content:
                logger.warning(
                    f"Received empty or unsupported message type: {chatbot_msg.message_type}"
                )
                return AckMessage.STATUS_OK, "OK"

            sender_id = chatbot_msg.sender_staff_id or chatbot_msg.sender_id
            sender_name = chatbot_msg.sender_nick or "Unknown"

            logger.info(f"Received DingTalk message from {sender_name} ({sender_id}): {content}")

            # Forward to Nanobot via _on_message (non-blocking).
            # Store reference to prevent GC before task completes.
            task = asyncio.create_task(
                self.channel._on_message(content, sender_id, sender_name)
            )
            self.channel._background_tasks.add(task)
            task.add_done_callback(self.channel._background_tasks.discard)

            return AckMessage.STATUS_OK, "OK"

        except Exception as e:
            logger.error(f"Error processing DingTalk message: {e}")
            # Return OK to avoid retry loop from DingTalk server
            return AckMessage.STATUS_OK, "Error"


class DingTalkChannel(BaseChannel):
    """
    使用Stream模式的钉钉渠道。

    使用WebSocket通过`dingtalk-stream` SDK接收事件。
    使用直接HTTP API发送消息（SDK主要用于接收）。

    注意：目前仅支持私聊（1对1）。群消息会被接收，
    但回复会作为私聊消息发送给发送者。
    """

    name = "dingtalk"

    def __init__(self, config: DingTalkConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: DingTalkConfig = config
        self._client: Any = None
        self._http: httpx.AsyncClient | None = None

        # Access Token management for sending messages
        self._access_token: str | None = None
        self._token_expiry: float = 0

        # Hold references to background tasks to prevent GC
        self._background_tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        """
        使用Stream模式启动钉钉机器人。

        初始化钉钉Stream客户端并启动长连接，接收来自钉钉的消息事件。
        包含自动重连逻辑，当连接异常断开时会自动重试。
        """
        try:
            if not DINGTALK_AVAILABLE:
                logger.error(
                    "DingTalk Stream SDK not installed. Run: pip install dingtalk-stream"
                )
                return

            if not self.config.client_id or not self.config.client_secret:
                logger.error("DingTalk client_id and client_secret not configured")
                return

            self._running = True
            self._http = httpx.AsyncClient()

            logger.info(
                f"Initializing DingTalk Stream Client with Client ID: {self.config.client_id}..."
            )
            credential = Credential(self.config.client_id, self.config.client_secret)
            self._client = DingTalkStreamClient(credential)

            # 注册标准处理器
            handler = NanobotDingTalkHandler(self)
            self._client.register_callback_handler(ChatbotMessage.TOPIC, handler)

            logger.info("DingTalk bot started with Stream Mode")

            # 重连循环：当SDK退出或崩溃时重新启动Stream
            while self._running:
                try:
                    await self._client.start()
                except Exception as e:
                    logger.warning(f"DingTalk stream error: {e}")
                if self._running:
                    logger.info("Reconnecting DingTalk stream in 5 seconds...")
                    await asyncio.sleep(5)

        except Exception as e:
            logger.exception(f"Failed to start DingTalk channel: {e}")

    async def stop(self) -> None:
        """
        停止钉钉机器人。

        关闭HTTP客户端并取消所有后台任务。
        """
        self._running = False
        # 关闭共享HTTP客户端
        if self._http:
            await self._http.aclose()
            self._http = None
        # 取消所有仍在运行的后台任务
        for task in self._background_tasks:
            task.cancel()
        self._background_tasks.clear()

    async def _get_access_token(self) -> str | None:
        """
        获取或刷新Access Token。

        优先使用未过期的缓存Token，如果已过期则向钉钉API请求新的Token。

        Returns:
            可用的Access Token，如果失败则返回None
        """
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token

        url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
        data = {
            "appKey": self.config.client_id,
            "appSecret": self.config.client_secret,
        }

        if not self._http:
            logger.warning("DingTalk HTTP client not initialized, cannot refresh token")
            return None

        try:
            resp = await self._http.post(url, json=data)
            resp.raise_for_status()
            res_data = resp.json()
            self._access_token = res_data.get("accessToken")
            # 提前60秒过期以保证安全
            self._token_expiry = time.time() + int(res_data.get("expireIn", 7200)) - 60
            return self._access_token
        except Exception as e:
            logger.error(f"Failed to get DingTalk access token: {e}")
            return None

    async def send(self, msg: OutboundMessage) -> None:
        """
        通过钉钉发送消息。

        使用机器人接口向指定用户发送Markdown消息。

        Args:
            msg: 出站消息对象
        """
        token = await self._get_access_token()
        if not token:
            return

        # oToMessages/batchSend: 向单个用户发送（私聊）
        # 文档：https://open.dingtalk.com/document/orgapp/robot-batch-send-messages
        url = "https://api.dingtalk.com/v1.0/robot/oToMessages/batchSend"

        headers = {"x-acs-dingtalk-access-token": token}

        data = {
            "robotCode": self.config.client_id,
            "userIds": [msg.chat_id],  # chat_id为用户的staffId
            "msgKey": "sampleMarkdown",
            "msgParam": json.dumps({
                "text": msg.content,
                "title": "Nanobot Reply",
            }),
        }

        if not self._http:
            logger.warning("DingTalk HTTP client not initialized, cannot send")
            return

        try:
            resp = await self._http.post(url, json=data, headers=headers)
            if resp.status_code != 200:
                logger.error(f"DingTalk send failed: {resp.text}")
            else:
                logger.debug(f"DingTalk message sent to {msg.chat_id}")
        except Exception as e:
            logger.error(f"Error sending DingTalk message: {e}")

    async def _on_message(self, content: str, sender_id: str, sender_name: str) -> None:
        """
        处理入站消息（由NanobotDingTalkHandler调用）。

        委托给BaseChannel._handle_message()，在发布到总线前进行allow_from权限校验。

        Args:
            content: 消息内容
            sender_id: 发送者ID
            sender_name: 发送者名称
        """
        try:
            logger.info(f"DingTalk inbound: {content} from {sender_name}")
            await self._handle_message(
                sender_id=sender_id,
                chat_id=sender_id,  # For private chat, chat_id == sender_id
                content=str(content),
                metadata={
                    "sender_name": sender_name,
                    "platform": "dingtalk",
                },
            )
        except Exception as e:
            logger.error(f"Error publishing DingTalk message: {e}")
