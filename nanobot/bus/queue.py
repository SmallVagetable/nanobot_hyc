"""用于解耦渠道-智能体通信的异步消息队列。

此模块实现了消息总线，用于在聊天渠道和智能体核心之间传递消息。
通过消息队列实现了解耦，使得渠道和智能体可以独立运行和扩展。
"""

import asyncio
from typing import Callable, Awaitable

from loguru import logger

from nanobot.bus.events import InboundMessage, OutboundMessage


class MessageBus:
    """
    异步消息总线，用于解耦聊天渠道和智能体核心。
    
    消息总线使用两个队列：
    - inbound队列：渠道推送消息到队列，智能体从队列消费
    - outbound队列：智能体推送响应到队列，渠道从队列消费
    
    这种设计使得渠道和智能体可以独立运行，互不干扰。
    """
    
    def __init__(self):
        """初始化消息总线，创建入站和出站队列。"""
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()  # 入站消息队列
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()  # 出站消息队列
        self._outbound_subscribers: dict[str, list[Callable[[OutboundMessage], Awaitable[None]]]] = {}  # 出站消息订阅者
        self._running = False  # 分发器运行状态
    
    async def publish_inbound(self, msg: InboundMessage) -> None:
        """
        发布来自渠道的消息到入站队列。
        
        Args:
            msg: 入站消息
        """
        await self.inbound.put(msg)
    
    async def consume_inbound(self) -> InboundMessage:
        """
        消费下一条入站消息（阻塞直到有消息可用）。
        
        Returns:
            下一条入站消息
        """
        return await self.inbound.get()
    
    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """
        发布来自智能体的响应到出站队列。
        
        Args:
            msg: 出站消息
        """
        await self.outbound.put(msg)
    
    async def consume_outbound(self) -> OutboundMessage:
        """
        消费下一条出站消息（阻塞直到有消息可用）。
        
        Returns:
            下一条出站消息
        """
        return await self.outbound.get()
    
    def subscribe_outbound(
        self, 
        channel: str, 
        callback: Callable[[OutboundMessage], Awaitable[None]]
    ) -> None:
        """
        订阅特定渠道的出站消息。
        
        当有消息发送到指定渠道时，会调用注册的回调函数。
        
        Args:
            channel: 渠道名称
            callback: 回调函数，接收OutboundMessage并异步处理
        """
        if channel not in self._outbound_subscribers:
            self._outbound_subscribers[channel] = []
        self._outbound_subscribers[channel].append(callback)
    
    async def dispatch_outbound(self) -> None:
        """
        将出站消息分发给订阅的渠道。
        
        此方法应该作为后台任务运行，持续监听出站队列并将消息
        分发给相应渠道的订阅者。
        """
        self._running = True
        while self._running:
            try:
                msg = await asyncio.wait_for(self.outbound.get(), timeout=1.0)
                subscribers = self._outbound_subscribers.get(msg.channel, [])
                for callback in subscribers:
                    try:
                        await callback(msg)
                    except Exception as e:
                        logger.error(f"Error dispatching to {msg.channel}: {e}")
            except asyncio.TimeoutError:
                continue
    
    def stop(self) -> None:
        """
        停止分发器循环。
        
        设置运行标志为False，分发器会在下一次迭代时退出。
        """
        self._running = False
    
    @property
    def inbound_size(self) -> int:
        """
        获取待处理的入站消息数量。
        
        Returns:
            入站队列中的消息数量
        """
        return self.inbound.qsize()
    
    @property
    def outbound_size(self) -> int:
        """
        获取待处理的出站消息数量。
        
        Returns:
            出站队列中的消息数量
        """
        return self.outbound.qsize()
