"""智能体的持久化记忆系统。

此模块实现了智能体的记忆存储功能，支持两种类型的记忆：
1. 长期记忆：存储在 MEMORY.md 中，用于保存重要的持久化信息
2. 每日笔记：按日期存储在 memory/YYYY-MM-DD.md 中，用于记录日常活动
"""

from pathlib import Path
from datetime import datetime

from nanobot.utils.helpers import ensure_dir, today_date


class MemoryStore:
    """
    智能体的记忆存储系统。
    
    支持两种类型的记忆存储：
    - 每日笔记：按日期存储在 memory/YYYY-MM-DD.md 文件中
    - 长期记忆：存储在 memory/MEMORY.md 文件中，用于保存跨会话的重要信息
    
    记忆系统允许智能体在会话之间保持上下文，记住用户偏好、重要事实等信息。
    """
    
    def __init__(self, workspace: Path):
        """
        初始化记忆存储系统。
        
        Args:
            workspace: 工作空间路径，记忆文件将存储在工作空间的 memory 目录下
        """
        self.workspace = workspace
        self.memory_dir = ensure_dir(workspace / "memory")
        self.memory_file = self.memory_dir / "MEMORY.md"
    
    def get_today_file(self) -> Path:
        """
        获取今天的记忆文件路径。
        
        Returns:
            今天日期对应的记忆文件路径（格式：memory/YYYY-MM-DD.md）
        """
        return self.memory_dir / f"{today_date()}.md"
    
    def read_today(self) -> str:
        """
        读取今天的记忆笔记内容。
        
        Returns:
            今天的记忆内容，如果文件不存在则返回空字符串
        """
        today_file = self.get_today_file()
        if today_file.exists():
            return today_file.read_text(encoding="utf-8")
        return ""
    
    def append_today(self, content: str) -> None:
        """
        向今天的记忆笔记追加内容。
        
        如果今天的文件不存在，会自动创建并添加日期标题。
        如果文件已存在，则在新内容前添加换行符。
        
        Args:
            content: 要追加的内容
        """
        today_file = self.get_today_file()
        
        if today_file.exists():
            existing = today_file.read_text(encoding="utf-8")
            content = existing + "\n" + content
        else:
            # 为新的一天添加标题
            header = f"# {today_date()}\n\n"
            content = header + content
        
        today_file.write_text(content, encoding="utf-8")
    
    def read_long_term(self) -> str:
        """
        读取长期记忆内容。
        
        Returns:
            MEMORY.md 文件的内容，如果文件不存在则返回空字符串
        """
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding="utf-8")
        return ""
    
    def write_long_term(self, content: str) -> None:
        """
        写入长期记忆。
        
        此方法会完全覆盖 MEMORY.md 文件的内容。
        用于保存需要跨会话持久化的重要信息。
        
        Args:
            content: 要写入的内容
        """
        self.memory_file.write_text(content, encoding="utf-8")
    
    def get_recent_memories(self, days: int = 7) -> str:
        """
        获取最近N天的记忆内容。
        
        从今天开始向前回溯指定天数，收集所有存在的记忆文件内容。
        文件之间使用分隔符连接。
        
        Args:
            days: 要回溯的天数，默认为7天
        
        Returns:
            合并后的记忆内容，多个文件之间用分隔符连接
        """
        from datetime import timedelta
        
        memories = []
        today = datetime.now().date()
        
        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            file_path = self.memory_dir / f"{date_str}.md"
            
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                memories.append(content)
        
        return "\n\n---\n\n".join(memories)
    
    def list_memory_files(self) -> list[Path]:
        """
        列出所有记忆文件，按日期排序（最新的在前）。
        
        Returns:
            记忆文件路径列表，按日期降序排列
        """
        if not self.memory_dir.exists():
            return []
        
        files = list(self.memory_dir.glob("????-??-??.md"))
        return sorted(files, reverse=True)
    
    def get_memory_context(self) -> str:
        """
        获取用于智能体上下文的记忆内容。
        
        此方法会组合长期记忆和今天的笔记，格式化为适合添加到
        智能体系统提示中的格式。
        
        Returns:
            格式化的记忆上下文，包括长期记忆和今天的笔记
        """
        parts = []
        
        # 长期记忆
        long_term = self.read_long_term()
        if long_term:
            parts.append("## Long-term Memory\n" + long_term)
        
        # 今天的笔记
        today = self.read_today()
        if today:
            parts.append("## Today's Notes\n" + today)
        
        return "\n\n".join(parts) if parts else ""
