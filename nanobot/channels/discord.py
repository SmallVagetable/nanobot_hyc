"""使用Discord Gateway WebSocket实现的Discord渠道。

此模块实现了Discord聊天渠道，使用Discord Gateway WebSocket协议
进行实时通信。支持文本消息、附件、回复等功能。
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx
import websockets
from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import DiscordConfig


DISCORD_API_BASE = "https://discord.com/api/v10"  # Discord API基础URL
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024  # 20MB，最大附件大小


class DiscordChannel(BaseChannel):
    """
    使用Gateway WebSocket的Discord渠道。
    
    通过Discord Gateway WebSocket协议连接，支持实时消息接收。
    使用Discord REST API发送消息，支持速率限制处理。
    """

    name = "discord"

    def __init__(self, config: DiscordConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: DiscordConfig = config
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._seq: int | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._typing_tasks: dict[str, asyncio.Task] = {}
        self._http: httpx.AsyncClient | None = None

    async def start(self) -> None:
        """
        启动Discord Gateway连接。
        
        连接到Discord Gateway WebSocket，开始监听消息。
        支持自动重连，当连接断开时会自动尝试重新连接。
        """
        if not self.config.token:
            logger.error("Discord bot token not configured")
            return

        self._running = True
        
        # 配置 HTTP 客户端代理
        http_proxy = self.config.proxy if self.config.proxy else None
        self._http = httpx.AsyncClient(timeout=30.0, proxy=http_proxy)

        while self._running:
            original_proxies = {}
            try:
                logger.info("Connecting to Discord gateway...")
                # 配置 WebSocket 代理
                # websockets 库会自动从环境变量读取代理，如果需要自定义代理，
                # 可以在连接前临时设置环境变量
                if self.config.proxy:
                    # 保存原始环境变量
                    for key in ['https_proxy', 'http_proxy', 'all_proxy', 'HTTPS_PROXY', 'HTTP_PROXY', 'ALL_PROXY']:
                        original_proxies[key] = os.environ.get(key)
                    # 设置代理环境变量（websockets 会读取这些）
                    # 对于 SOCKS5，使用 all_proxy；对于 HTTP，使用 https_proxy
                    if self.config.proxy.startswith('socks5://'):
                        os.environ['ALL_PROXY'] = self.config.proxy
                    else:
                        os.environ['HTTPS_PROXY'] = self.config.proxy
                        os.environ['HTTP_PROXY'] = self.config.proxy
                
                async with websockets.connect(self.config.gateway_url) as ws:
                    self._ws = ws
                    await self._gateway_loop()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Discord gateway error: {e}")
                if self._running:
                    logger.info("Reconnecting to Discord gateway in 5 seconds...")
                    await asyncio.sleep(5)
            finally:
                # 恢复原始环境变量
                if original_proxies:
                    for key, value in original_proxies.items():
                        if value is None:
                            os.environ.pop(key, None)
                        else:
                            os.environ[key] = value

    async def stop(self) -> None:
        """
        停止Discord渠道。
        
        取消心跳任务和打字任务，关闭WebSocket和HTTP连接。
        """
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        for task in self._typing_tasks.values():
            task.cancel()
        self._typing_tasks.clear()
        if self._ws:
            await self._ws.close()
            self._ws = None
        if self._http:
            await self._http.aclose()
            self._http = None

    async def send(self, msg: OutboundMessage) -> None:
        """
        通过Discord REST API发送消息。
        
        使用Discord REST API发送消息，支持回复功能。
        自动处理速率限制，如果被限流会等待后重试。
        
        Args:
            msg: 要发送的出站消息
        """
        if not self._http:
            logger.warning("Discord HTTP client not initialized")
            return

        url = f"{DISCORD_API_BASE}/channels/{msg.chat_id}/messages"
        payload: dict[str, Any] = {"content": msg.content}

        if msg.reply_to:
            payload["message_reference"] = {"message_id": msg.reply_to}
            payload["allowed_mentions"] = {"replied_user": False}

        headers = {"Authorization": f"Bot {self.config.token}"}

        try:
            for attempt in range(3):
                try:
                    response = await self._http.post(url, headers=headers, json=payload)
                    if response.status_code == 429:
                        # 速率限制，等待后重试
                        data = response.json()
                        retry_after = float(data.get("retry_after", 1.0))
                        logger.warning(f"Discord rate limited, retrying in {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    if response.status_code >= 400:
                        try:
                            body = response.json()
                            code = body.get("code")
                            msg_discord = body.get("message", "")
                            # 10003=Unknown Channel, 50001=Missing Access, 50013=Missing Permissions
                            hint = ""
                            if code == 10003:
                                hint = "频道对机器人不可见：确认 (1) 机器人已加入该频道所在服务器 (2) 频道未删除。"
                            elif code in (50001, 50013):
                                hint = "机器人无权限：在该频道/服务器给机器人角色勾选「查看频道」和「发送消息」。"
                            if hint:
                                logger.error(f"Discord send failed: code={code}, message={msg_discord}. {hint}")
                            else:
                                logger.error(f"Discord send failed: code={code}, message={msg_discord}")
                        except Exception:
                            logger.error(f"Discord send failed: {response.status_code} {response.text}")
                        return
                    return
                except Exception as e:
                    if attempt == 2:
                        err = str(e)
                        if "404" in err:
                            logger.error(
                                f"Error sending Discord message: {e}. "
                                "若确认是频道 ID，请检查：(1) 机器人是否已加入该频道所在服务器 (2) 该频道是否对机器人开放「查看频道」和「发送消息」。"
                            )
                        else:
                            logger.error(f"Error sending Discord message: {e}")
                    else:
                        await asyncio.sleep(1)
        finally:
            await self._stop_typing(msg.chat_id)

    async def _gateway_loop(self) -> None:
        """
        主Gateway循环：身份验证、心跳、分发事件。
        
        处理Discord Gateway的所有事件，包括：
        - HELLO: 启动心跳和身份验证
        - READY: 连接就绪
        - MESSAGE_CREATE: 新消息
        - RECONNECT: 请求重连
        - INVALID_SESSION: 会话无效
        """
        if not self._ws:
            return

        async for raw in self._ws:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from Discord gateway: {raw[:100]}")
                continue

            op = data.get("op")  # 操作码
            event_type = data.get("t")  # 事件类型
            seq = data.get("s")  # 序列号
            payload = data.get("d")  # 数据负载

            if seq is not None:
                self._seq = seq

            if op == 10:
                # HELLO: 启动心跳和身份验证
                interval_ms = payload.get("heartbeat_interval", 45000)
                await self._start_heartbeat(interval_ms / 1000)
                await self._identify()
            elif op == 0 and event_type == "READY":
                logger.info("Discord gateway READY")
            elif op == 0 and event_type == "MESSAGE_CREATE":
                await self._handle_message_create(payload)
            elif op == 7:
                # RECONNECT: 退出循环以重连
                logger.info("Discord gateway requested reconnect")
                break
            elif op == 9:
                # INVALID_SESSION: 重连
                logger.warning("Discord gateway invalid session")
                break

    async def _identify(self) -> None:
        """
        发送IDENTIFY负载到Discord Gateway。

        用于完成身份验证，声明Bot令牌和订阅的intents。
        """
        if not self._ws:
            return

        identify = {
            "op": 2,
            "d": {
                "token": self.config.token,
                "intents": self.config.intents,
                "properties": {
                    "os": "nanobot",
                    "browser": "nanobot",
                    "device": "nanobot",
                },
            },
        }
        await self._ws.send(json.dumps(identify))

    async def _start_heartbeat(self, interval_s: float) -> None:
        """
        启动或重启心跳循环。

        按指定间隔向Gateway发送心跳包，以保持连接存活。
        """
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        async def heartbeat_loop() -> None:
            while self._running and self._ws:
                payload = {"op": 1, "d": self._seq}
                try:
                    await self._ws.send(json.dumps(payload))
                except Exception as e:
                    logger.warning(f"Discord heartbeat failed: {e}")
                    break
                await asyncio.sleep(interval_s)

        self._heartbeat_task = asyncio.create_task(heartbeat_loop())

    async def _handle_message_create(self, payload: dict[str, Any]) -> None:
        """
        处理来自Discord的入站消息事件。

        过滤掉机器人消息，提取发送者、频道和消息内容，并转发到消息总线。
        """
        author = payload.get("author") or {}
        if author.get("bot"):
            return

        sender_id = str(author.get("id", ""))
        channel_id = str(payload.get("channel_id", ""))
        content = payload.get("content") or ""

        if not sender_id or not channel_id:
            return

        if not self.is_allowed(sender_id):
            return

        content_parts = [content] if content else []
        media_paths: list[str] = []
        media_dir = Path.home() / ".nanobot" / "media"

        for attachment in payload.get("attachments") or []:
            url = attachment.get("url")
            filename = attachment.get("filename") or "attachment"
            size = attachment.get("size") or 0
            if not url or not self._http:
                continue
            if size and size > MAX_ATTACHMENT_BYTES:
                content_parts.append(f"[attachment: {filename} - too large]")
                continue
            try:
                media_dir.mkdir(parents=True, exist_ok=True)
                file_path = media_dir / f"{attachment.get('id', 'file')}_{filename.replace('/', '_')}"
                resp = await self._http.get(url)
                resp.raise_for_status()
                file_path.write_bytes(resp.content)
                media_paths.append(str(file_path))
                content_parts.append(f"[attachment: {file_path}]")
            except Exception as e:
                logger.warning(f"Failed to download Discord attachment: {e}")
                content_parts.append(f"[attachment: {filename} - download failed]")

        reply_to = (payload.get("referenced_message") or {}).get("id")

        logger.debug(f"Discord channel_id={channel_id} (cron --to 填此值可投递到本频道)")

        await self._start_typing(channel_id)

        await self._handle_message(
            sender_id=sender_id,
            chat_id=channel_id,
            content="\n".join(p for p in content_parts if p) or "[empty message]",
            media=media_paths,
            metadata={
                "message_id": str(payload.get("id", "")),
                "guild_id": payload.get("guild_id"),
                "reply_to": reply_to,
            },
        )

    async def _start_typing(self, channel_id: str) -> None:
        """
        为指定频道启动周期性的“正在输入”指示器。

        Args:
            channel_id: Discord频道ID
        """
        await self._stop_typing(channel_id)

        async def typing_loop() -> None:
            url = f"{DISCORD_API_BASE}/channels/{channel_id}/typing"
            headers = {"Authorization": f"Bot {self.config.token}"}
            while self._running:
                try:
                    await self._http.post(url, headers=headers)
                except Exception:
                    pass
                await asyncio.sleep(8)

        self._typing_tasks[channel_id] = asyncio.create_task(typing_loop())

    async def _stop_typing(self, channel_id: str) -> None:
        """
        停止指定频道的“正在输入”指示器。

        Args:
            channel_id: Discord频道ID
        """
        task = self._typing_tasks.pop(channel_id, None)
        if task:
            task.cancel()
