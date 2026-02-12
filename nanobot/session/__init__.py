"""会话管理模块。

此模块提供了对话会话的管理功能，用于存储和管理不同用户/渠道的对话历史。
"""

from nanobot.session.manager import SessionManager, Session

__all__ = ["SessionManager", "Session"]
