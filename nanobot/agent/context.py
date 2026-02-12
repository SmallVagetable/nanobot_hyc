"""上下文构建器，用于组装智能体的提示词。

此模块负责构建智能体的完整上下文，包括系统提示词和消息列表。
它将引导文件、记忆、技能和对话历史组合成连贯的提示词供LLM使用。
"""

import base64
import mimetypes
import platform
from pathlib import Path
from typing import Any

from nanobot.agent.memory import MemoryStore
from nanobot.agent.skills import SkillsLoader


class ContextBuilder:
    """
    构建智能体的上下文（系统提示词 + 消息列表）。
    
    此类负责将以下内容组装成连贯的提示词：
    - 引导文件（bootstrap files）：定义智能体的身份、行为准则等
    - 记忆内容：长期记忆和每日笔记
    - 技能信息：可用技能及其描述
    - 对话历史：之前的对话消息
    
    通过这种方式，智能体可以获得完整的上下文信息，从而做出更准确的响应。
    """
    
    # 引导文件列表，这些文件定义了智能体的核心配置
    BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]
    
    def __init__(self, workspace: Path):
        """
        初始化上下文构建器。
        
        Args:
            workspace: 工作空间路径，用于加载引导文件和记忆
        """
        self.workspace = workspace
        self.memory = MemoryStore(workspace)
        self.skills = SkillsLoader(workspace)
    
    def build_system_prompt(self, skill_names: list[str] | None = None) -> str:
        """
        从引导文件、记忆和技能构建系统提示词。
        
        系统提示词包含智能体的身份、能力、工作空间信息等核心内容。
        采用渐进式加载策略：总是加载的技能包含完整内容，其他技能只显示摘要。
        
        Args:
            skill_names: 可选的要包含的技能名称列表（当前未使用，保留用于未来扩展）
        
        Returns:
            完整的系统提示词字符串
        """
        parts = []
        
        # 核心身份信息
        parts.append(self._get_identity())
        
        # 引导文件内容
        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)
        
        # 记忆上下文
        memory = self.memory.get_memory_context()
        if memory:
            parts.append(f"# Memory\n\n{memory}")
        
        # 技能 - 渐进式加载策略
        # 1. 总是加载的技能：包含完整内容
        always_skills = self.skills.get_always_skills()
        if always_skills:
            always_content = self.skills.load_skills_for_context(always_skills)
            if always_content:
                parts.append(f"# Active Skills\n\n{always_content}")
        
        # 2. 可用技能：只显示摘要（智能体需要使用read_file工具来加载完整内容）
        skills_summary = self.skills.build_skills_summary()
        if skills_summary:
            parts.append(f"""# Skills

The following skills extend your capabilities. To use a skill, read its SKILL.md file using the read_file tool.
Skills with available="false" need dependencies installed first - you can try installing them with apt/brew.

{skills_summary}""")
        
        return "\n\n---\n\n".join(parts)
    
    def _get_identity(self) -> str:
        """
        获取核心身份信息部分。
        
        包含智能体的基本介绍、当前时间、运行环境、工作空间路径等。
        
        Returns:
            格式化的身份信息字符串
        """
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        workspace_path = str(self.workspace.expanduser().resolve())
        system = platform.system()
        runtime = f"{'macOS' if system == 'Darwin' else system} {platform.machine()}, Python {platform.python_version()}"
        
        return f"""# nanobot 🐈

You are nanobot, a helpful AI assistant. You have access to tools that allow you to:
- Read, write, and edit files
- Execute shell commands
- Search the web and fetch web pages
- Send messages to users on chat channels
- Spawn subagents for complex background tasks

## Current Time
{now}

## Runtime
{runtime}

## Workspace
Your workspace is at: {workspace_path}
- Memory files: {workspace_path}/memory/MEMORY.md
- Daily notes: {workspace_path}/memory/YYYY-MM-DD.md
- Custom skills: {workspace_path}/skills/{{skill-name}}/SKILL.md

IMPORTANT: When responding to direct questions or conversations, reply directly with your text response.
Only use the 'message' tool when you need to send a message to a specific chat channel (like WhatsApp).
For normal conversation, just respond with text - do not call the message tool.

Always be helpful, accurate, and concise. When using tools, explain what you're doing.
When remembering something, write to {workspace_path}/memory/MEMORY.md"""
    
    def _load_bootstrap_files(self) -> str:
        """
        从工作空间加载所有引导文件。
        
        引导文件定义了智能体的核心配置，包括：
        - AGENTS.md: 智能体指令
        - SOUL.md: 智能体的个性和价值观
        - USER.md: 用户信息
        - TOOLS.md: 工具说明
        - IDENTITY.md: 身份定义
        
        Returns:
            所有引导文件内容的组合字符串，如果没有任何文件则返回空字符串
        """
        parts = []
        
        for filename in self.BOOTSTRAP_FILES:
            file_path = self.workspace / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n\n{content}")
        
        return "\n\n".join(parts) if parts else ""
    
    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        skill_names: list[str] | None = None,
        media: list[str] | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        构建用于LLM调用的完整消息列表。

        消息列表包括：
        1. 系统提示词（包含身份、记忆、技能等）
        2. 对话历史
        3. 当前用户消息（可能包含图片等媒体）

        Args:
            history: 之前的对话消息列表
            current_message: 新的用户消息
            skill_names: 可选的要包含的技能名称列表
            media: 可选的本地图片/媒体文件路径列表
            channel: 当前渠道（telegram、feishu等）
            chat_id: 当前聊天/用户ID

        Returns:
            包含系统提示词的完整消息列表
        """
        messages = []

        # 系统提示词
        system_prompt = self.build_system_prompt(skill_names)
        if channel and chat_id:
            system_prompt += f"\n\n## Current Session\nChannel: {channel}\nChat ID: {chat_id}"
        messages.append({"role": "system", "content": system_prompt})

        # 对话历史
        messages.extend(history)

        # 当前消息（可能包含图片附件）
        user_content = self._build_user_content(current_message, media)
        messages.append({"role": "user", "content": user_content})

        return messages

    def _build_user_content(self, text: str, media: list[str] | None) -> str | list[dict[str, Any]]:
        """
        构建用户消息内容，支持可选的base64编码图片。
        
        如果提供了媒体文件，会将图片编码为base64格式并添加到消息中。
        只处理图片类型的文件，其他类型会被忽略。
        
        Args:
            text: 文本消息内容
            media: 可选的媒体文件路径列表
        
        Returns:
            如果无媒体，返回文本字符串；如果有图片，返回包含图片和文本的列表
        """
        if not media:
            return text
        
        images = []
        for path in media:
            p = Path(path)
            mime, _ = mimetypes.guess_type(path)
            if not p.is_file() or not mime or not mime.startswith("image/"):
                continue
            b64 = base64.b64encode(p.read_bytes()).decode()
            images.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        
        if not images:
            return text
        return images + [{"type": "text", "text": text}]
    
    def add_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str
    ) -> list[dict[str, Any]]:
        """
        向消息列表添加工具执行结果。
        
        当工具执行完成后，需要将结果添加到消息历史中，以便LLM了解工具的执行情况。
        
        Args:
            messages: 当前消息列表
            tool_call_id: 工具调用的ID，用于关联工具调用和结果
            tool_name: 工具名称
            result: 工具执行结果
        
        Returns:
            更新后的消息列表
        """
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result
        })
        return messages
    
    def add_assistant_message(
        self,
        messages: list[dict[str, Any]],
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None,
        reasoning_content: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        向消息列表添加助手消息。
        
        助手消息可能包含：
        - 文本内容
        - 工具调用（如果需要执行工具）
        - 推理内容（对于支持思考过程的模型，如Kimi、DeepSeek-R1等）
        
        Args:
            messages: 当前消息列表
            content: 消息文本内容
            tool_calls: 可选的工具调用列表
            reasoning_content: 思考过程输出（用于支持思考过程的模型）
        
        Returns:
            更新后的消息列表
        """
        msg: dict[str, Any] = {"role": "assistant", "content": content or ""}
        
        if tool_calls:
            msg["tool_calls"] = tool_calls
        
        # 思考模型需要这个字段，否则会拒绝历史记录
        if reasoning_content:
            msg["reasoning_content"] = reasoning_content
        
        messages.append(msg)
        return messages
