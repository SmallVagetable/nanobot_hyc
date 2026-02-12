"""nanobot的实用工具函数。

此模块提供了各种辅助函数，用于路径管理、字符串处理、日期时间等常见操作。
"""

from pathlib import Path
from datetime import datetime


def ensure_dir(path: Path) -> Path:
    """
    确保目录存在，如果不存在则创建。
    
    Args:
        path: 目录路径
    
    Returns:
        目录路径（确保已存在）
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_data_path() -> Path:
    """
    获取nanobot数据目录路径（~/.nanobot）。
    
    Returns:
        数据目录路径
    """
    return ensure_dir(Path.home() / ".nanobot")


def get_workspace_path(workspace: str | None = None) -> Path:
    """
    获取工作空间路径。
    
    如果未指定工作空间路径，则使用默认路径 ~/.nanobot/workspace。
    
    Args:
        workspace: 可选的工作空间路径，如果为None则使用默认路径
    
    Returns:
        展开并确保存在的工作空间路径
    """
    if workspace:
        path = Path(workspace).expanduser()
    else:
        path = Path.home() / ".nanobot" / "workspace"
    return ensure_dir(path)


def get_sessions_path() -> Path:
    """
    获取会话存储目录路径。
    
    Returns:
        会话目录路径
    """
    return ensure_dir(get_data_path() / "sessions")


def get_memory_path(workspace: Path | None = None) -> Path:
    """
    获取工作空间内的记忆目录路径。
    
    Args:
        workspace: 可选的工作空间路径，如果为None则使用默认工作空间
    
    Returns:
        记忆目录路径
    """
    ws = workspace or get_workspace_path()
    return ensure_dir(ws / "memory")


def get_skills_path(workspace: Path | None = None) -> Path:
    """
    获取工作空间内的技能目录路径。
    
    Args:
        workspace: 可选的工作空间路径，如果为None则使用默认工作空间
    
    Returns:
        技能目录路径
    """
    ws = workspace or get_workspace_path()
    return ensure_dir(ws / "skills")


def today_date() -> str:
    """
    获取今天的日期，格式为YYYY-MM-DD。
    
    Returns:
        今天的日期字符串
    """
    return datetime.now().strftime("%Y-%m-%d")


def timestamp() -> str:
    """
    获取当前时间戳，ISO格式。
    
    Returns:
        当前时间戳字符串
    """
    return datetime.now().isoformat()


def truncate_string(s: str, max_len: int = 100, suffix: str = "...") -> str:
    """
    截断字符串到最大长度，如果被截断则添加后缀。
    
    Args:
        s: 要截断的字符串
        max_len: 最大长度，默认为100
        suffix: 截断时添加的后缀，默认为"..."
    
    Returns:
        截断后的字符串
    """
    if len(s) <= max_len:
        return s
    return s[: max_len - len(suffix)] + suffix


def safe_filename(name: str) -> str:
    """
    将字符串转换为安全的文件名。
    
    替换文件名中的不安全字符（如 < > : " / \ | ? *）为下划线。
    
    Args:
        name: 原始字符串
    
    Returns:
        安全的文件名
    """
    # 替换不安全字符
    unsafe = '<>:"/\\|?*'
    for char in unsafe:
        name = name.replace(char, "_")
    return name.strip()


def parse_session_key(key: str) -> tuple[str, str]:
    """
    将会话键解析为渠道和聊天ID。
    
    会话键格式为"channel:chat_id"，此函数将其拆分为两部分。
    
    Args:
        key: 会话键，格式为"channel:chat_id"
    
    Returns:
        包含(channel, chat_id)的元组
    
    Raises:
        ValueError: 如果会话键格式无效
    """
    parts = key.split(":", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid session key: {key}")
    return parts[0], parts[1]
