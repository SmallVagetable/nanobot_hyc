"""心跳服务 - 定期唤醒智能体检查任务。

心跳服务会定期唤醒智能体，让它检查工作空间中的HEARTBEAT.md文件。
如果文件中有任务或指令，智能体会执行它们；如果没有，则回复HEARTBEAT_OK。
"""

import asyncio
from pathlib import Path
from typing import Any, Callable, Coroutine

from loguru import logger

# 默认间隔：30分钟
DEFAULT_HEARTBEAT_INTERVAL_S = 30 * 60

# 心跳时发送给智能体的提示词
HEARTBEAT_PROMPT = """Read HEARTBEAT.md in your workspace (if it exists).
Follow any instructions or tasks listed there.
If nothing needs attention, reply with just: HEARTBEAT_OK"""

# 表示"无事可做"的标记
HEARTBEAT_OK_TOKEN = "HEARTBEAT_OK"


def _is_heartbeat_empty(content: str | None) -> bool:
    """
    检查HEARTBEAT.md是否没有可执行的内容。
    
    跳过空行、标题、HTML注释和空的复选框，只检查是否有实际的任务内容。
    
    Args:
        content: HEARTBEAT.md文件内容
    
    Returns:
        如果文件为空或没有可执行内容返回True，否则返回False
    """
    if not content:
        return True
    
    # 要跳过的行模式：空行、标题、HTML注释、空的复选框
    skip_patterns = {"- [ ]", "* [ ]", "- [x]", "* [x]"}
    
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("<!--") or line in skip_patterns:
            continue
        return False  # 找到可执行内容
    
    return True


class HeartbeatService:
    """
    定期心跳服务，用于唤醒智能体检查任务。
    
    心跳服务会定期（默认30分钟）唤醒智能体，让它读取工作空间中的
    HEARTBEAT.md文件并执行其中的任务。如果文件为空或没有需要处理的内容，
    智能体会回复HEARTBEAT_OK。
    
    这允许用户通过编辑HEARTBEAT.md文件来给智能体安排定期任务。
    """
    
    def __init__(
        self,
        workspace: Path,
        on_heartbeat: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        interval_s: int = DEFAULT_HEARTBEAT_INTERVAL_S,
        enabled: bool = True,
    ):
        self.workspace = workspace
        self.on_heartbeat = on_heartbeat
        self.interval_s = interval_s
        self.enabled = enabled
        self._running = False
        self._task: asyncio.Task | None = None
    
    @property
    def heartbeat_file(self) -> Path:
        return self.workspace / "HEARTBEAT.md"
    
    def _read_heartbeat_file(self) -> str | None:
        """Read HEARTBEAT.md content."""
        if self.heartbeat_file.exists():
            try:
                return self.heartbeat_file.read_text()
            except Exception:
                return None
        return None
    
    async def start(self) -> None:
        """Start the heartbeat service."""
        if not self.enabled:
            logger.info("Heartbeat disabled")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Heartbeat started (every {self.interval_s}s)")
    
    def stop(self) -> None:
        """Stop the heartbeat service."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
    
    async def _run_loop(self) -> None:
        """Main heartbeat loop."""
        while self._running:
            try:
                await asyncio.sleep(self.interval_s)
                if self._running:
                    await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
    
    async def _tick(self) -> None:
        """Execute a single heartbeat tick."""
        content = self._read_heartbeat_file()
        
        # Skip if HEARTBEAT.md is empty or doesn't exist
        if _is_heartbeat_empty(content):
            logger.debug("Heartbeat: no tasks (HEARTBEAT.md empty)")
            return
        
        logger.info("Heartbeat: checking for tasks...")
        
        if self.on_heartbeat:
            try:
                response = await self.on_heartbeat(HEARTBEAT_PROMPT)
                
                # Check if agent said "nothing to do"
                if HEARTBEAT_OK_TOKEN.replace("_", "") in response.upper().replace("_", ""):
                    logger.info("Heartbeat: OK (no action needed)")
                else:
                    logger.info(f"Heartbeat: completed task")
                    
            except Exception as e:
                logger.error(f"Heartbeat execution failed: {e}")
    
    async def trigger_now(self) -> str | None:
        """Manually trigger a heartbeat."""
        if self.on_heartbeat:
            return await self.on_heartbeat(HEARTBEAT_PROMPT)
        return None
