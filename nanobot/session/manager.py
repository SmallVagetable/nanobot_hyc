"""会话管理，用于管理对话历史。

此模块实现了会话管理系统，用于存储和管理不同用户/渠道的对话历史。
会话以JSONL格式存储，便于读取和持久化。
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from loguru import logger

from nanobot.utils.helpers import ensure_dir, safe_filename


@dataclass
class Session:
    """
    对话会话。
    
    一个会话代表一个用户在一个渠道上的对话历史。
    消息以JSONL格式存储，便于读取和持久化。
    """
    
    key: str  # 会话键，格式为"channel:chat_id"
    messages: list[dict[str, Any]] = field(default_factory=list)  # 消息列表
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)  # 更新时间
    metadata: dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """
        向会话添加消息。
        
        Args:
            role: 消息角色（user/assistant/system等）
            content: 消息内容
            **kwargs: 其他消息属性
        """
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        self.messages.append(msg)
        self.updated_at = datetime.now()
    
    def get_history(self, max_messages: int = 50) -> list[dict[str, Any]]:
        """
        获取用于LLM上下文的消息历史。
        
        返回最近的消息，限制在最大消息数以内。
        只返回role和content字段，符合LLM的消息格式要求。
        
        Args:
            max_messages: 要返回的最大消息数，默认为50
        
        Returns:
            LLM格式的消息列表
        """
        # 获取最近的消息
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        
        # 转换为LLM格式（只包含role和content）
        return [{"role": m["role"], "content": m["content"]} for m in recent]
    
    def clear(self) -> None:
        """
        清空会话中的所有消息。
        
        保留会话本身，只清空消息列表。
        """
        self.messages = []
        self.updated_at = datetime.now()


class SessionManager:
    """
    管理对话会话。
    
    会话管理器负责创建、加载、保存和删除会话。
    会话以JSONL格式存储在sessions目录中，每个会话对应一个文件。
    使用内存缓存提高访问性能。
    """
    
    def __init__(self, workspace: Path):
        """
        初始化会话管理器。
        
        Args:
            workspace: 工作空间路径（当前未使用，保留用于未来扩展）
        """
        self.workspace = workspace
        self.sessions_dir = ensure_dir(Path.home() / ".nanobot" / "sessions")
        self._cache: dict[str, Session] = {}  # 内存缓存，提高访问性能
    
    def _get_session_path(self, key: str) -> Path:
        """
        获取会话的文件路径。
        
        Args:
            key: 会话键
        
        Returns:
            会话文件的路径
        """
        safe_key = safe_filename(key.replace(":", "_"))
        return self.sessions_dir / f"{safe_key}.jsonl"
    
    def get_or_create(self, key: str) -> Session:
        """
        获取现有会话或创建新会话。
        
        首先检查内存缓存，如果不存在则尝试从磁盘加载，
        如果磁盘上也不存在则创建新会话。
        
        Args:
            key: 会话键（通常是"channel:chat_id"格式）
        
        Returns:
            会话对象
        """
        # 检查缓存
        if key in self._cache:
            return self._cache[key]
        
        # 尝试从磁盘加载
        session = self._load(key)
        if session is None:
            session = Session(key=key)
        
        self._cache[key] = session
        return session
    
    def _load(self, key: str) -> Session | None:
        """
        从磁盘加载会话。
        
        Args:
            key: 会话键
        
        Returns:
            会话对象，如果文件不存在或加载失败则返回None
        """
        path = self._get_session_path(key)
        
        if not path.exists():
            return None
        
        try:
            messages = []
            metadata = {}
            created_at = None
            
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    data = json.loads(line)
                    
                    if data.get("_type") == "metadata":
                        # 元数据行
                        metadata = data.get("metadata", {})
                        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
                    else:
                        # 消息行
                        messages.append(data)
            
            return Session(
                key=key,
                messages=messages,
                created_at=created_at or datetime.now(),
                metadata=metadata
            )
        except Exception as e:
            logger.warning(f"Failed to load session {key}: {e}")
            return None
    
    def save(self, session: Session) -> None:
        """
        将会话保存到磁盘。
        
        会话以JSONL格式保存，第一行是元数据，后续行是消息。
        
        Args:
            session: 要保存的会话
        """
        path = self._get_session_path(session.key)
        
        with open(path, "w") as f:
            # 首先写入元数据
            metadata_line = {
                "_type": "metadata",
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.metadata
            }
            f.write(json.dumps(metadata_line) + "\n")
            
            # 写入消息
            for msg in session.messages:
                f.write(json.dumps(msg) + "\n")
        
        self._cache[session.key] = session
    
    def delete(self, key: str) -> bool:
        """
        删除会话。
        
        从内存缓存和磁盘文件中删除会话。
        
        Args:
            key: 会话键
        
        Returns:
            如果删除成功返回True，如果会话不存在返回False
        """
        # 从缓存中移除
        self._cache.pop(key, None)
        
        # 删除文件
        path = self._get_session_path(key)
        if path.exists():
            path.unlink()
            return True
        return False
    
    def list_sessions(self) -> list[dict[str, Any]]:
        """
        列出所有会话。
        
        扫描sessions目录，读取每个会话文件的元数据。
        
        Returns:
            会话信息字典列表，按更新时间降序排列
        """
        sessions = []
        
        for path in self.sessions_dir.glob("*.jsonl"):
            try:
                # 只读取元数据行
                with open(path) as f:
                    first_line = f.readline().strip()
                    if first_line:
                        data = json.loads(first_line)
                        if data.get("_type") == "metadata":
                            sessions.append({
                                "key": path.stem.replace("_", ":"),
                                "created_at": data.get("created_at"),
                                "updated_at": data.get("updated_at"),
                                "path": str(path)
                            })
            except Exception:
                continue
        
        return sorted(sessions, key=lambda x: x.get("updated_at", ""), reverse=True)
