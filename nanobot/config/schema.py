"""使用Pydantic的配置模式定义。

此模块定义了nanobot的所有配置结构，包括：
- 各种聊天渠道的配置（WhatsApp、Telegram、Discord等）
- LLM提供者配置
- 智能体默认配置
- 工具配置
- 网关配置

所有配置类都继承自Pydantic的BaseModel，提供类型验证和自动文档生成。
"""

from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from pydantic_settings import BaseSettings


class WhatsAppConfig(BaseModel):
    """WhatsApp渠道配置。"""
    enabled: bool = False  # 是否启用
    bridge_url: str = "ws://localhost:3001"  # WhatsApp桥接服务URL
    allow_from: list[str] = Field(default_factory=list)  # 允许的来电号码列表


class TelegramConfig(BaseModel):
    """Telegram渠道配置。"""
    enabled: bool = False  # 是否启用
    token: str = ""  # 机器人令牌（从@BotFather获取）
    allow_from: list[str] = Field(default_factory=list)  # 允许的用户ID或用户名列表
    proxy: str | None = None  # HTTP/SOCKS5代理URL，例如"http://127.0.0.1:7890"或"socks5://127.0.0.1:1080"


class FeishuConfig(BaseModel):
    """飞书/Lark渠道配置，使用WebSocket长连接。"""
    enabled: bool = False  # 是否启用
    app_id: str = ""  # 应用ID（从飞书开放平台获取）
    app_secret: str = ""  # 应用密钥（从飞书开放平台获取）
    encrypt_key: str = ""  # 事件订阅的加密密钥（可选）
    verification_token: str = ""  # 事件订阅的验证令牌（可选）
    allow_from: list[str] = Field(default_factory=list)  # 允许的用户open_id列表


class DingTalkConfig(BaseModel):
    """钉钉渠道配置，使用Stream模式。"""
    enabled: bool = False  # 是否启用
    client_id: str = ""  # 应用Key（AppKey）
    client_secret: str = ""  # 应用密钥（AppSecret）
    allow_from: list[str] = Field(default_factory=list)  # 允许的员工ID列表


class DiscordConfig(BaseModel):
    """Discord渠道配置。"""
    enabled: bool = False  # 是否启用
    token: str = ""  # 机器人令牌（从Discord开发者门户获取）
    allow_from: list[str] = Field(default_factory=list)  # 允许的用户ID列表
    gateway_url: str = "wss://gateway.discord.gg/?v=10&encoding=json"  # Discord网关URL
    intents: int = 37377  # 意图标志：GUILDS + GUILD_MESSAGES + DIRECT_MESSAGES + MESSAGE_CONTENT
    proxy: str | None = None  # HTTP/SOCKS5代理URL，例如"http://127.0.0.1:7890"或"socks5://127.0.0.1:7890"

class EmailConfig(BaseModel):
    """邮件渠道配置（IMAP接收 + SMTP发送）。"""
    enabled: bool = False  # 是否启用
    consent_granted: bool = False  # 明确的所有者许可，允许访问邮箱数据

    # IMAP配置（接收邮件）
    imap_host: str = ""  # IMAP服务器地址
    imap_port: int = 993  # IMAP端口
    imap_username: str = ""  # IMAP用户名
    imap_password: str = ""  # IMAP密码
    imap_mailbox: str = "INBOX"  # 邮箱名称
    imap_use_ssl: bool = True  # 是否使用SSL

    # SMTP配置（发送邮件）
    smtp_host: str = ""  # SMTP服务器地址
    smtp_port: int = 587  # SMTP端口
    smtp_username: str = ""  # SMTP用户名
    smtp_password: str = ""  # SMTP密码
    smtp_use_tls: bool = True  # 是否使用TLS
    smtp_use_ssl: bool = False  # 是否使用SSL
    from_address: str = ""  # 发件人地址

    # 行为配置
    auto_reply_enabled: bool = True  # 如果为False，接收邮件但不自动回复
    poll_interval_seconds: int = 30  # 轮询间隔（秒）
    mark_seen: bool = True  # 是否标记为已读
    max_body_chars: int = 12000  # 邮件正文最大字符数
    subject_prefix: str = "Re: "  # 回复主题前缀
    allow_from: list[str] = Field(default_factory=list)  # 允许的发件人邮箱地址列表


class MochatMentionConfig(BaseModel):
    """Mochat mention behavior configuration."""
    require_in_groups: bool = False


class MochatGroupRule(BaseModel):
    """Mochat per-group mention requirement."""
    require_mention: bool = False


class MochatConfig(BaseModel):
    """Mochat channel configuration."""
    enabled: bool = False
    base_url: str = "https://mochat.io"
    socket_url: str = ""
    socket_path: str = "/socket.io"
    socket_disable_msgpack: bool = False
    socket_reconnect_delay_ms: int = 1000
    socket_max_reconnect_delay_ms: int = 10000
    socket_connect_timeout_ms: int = 10000
    refresh_interval_ms: int = 30000
    watch_timeout_ms: int = 25000
    watch_limit: int = 100
    retry_delay_ms: int = 500
    max_retry_attempts: int = 0  # 0 means unlimited retries
    claw_token: str = ""
    agent_user_id: str = ""
    sessions: list[str] = Field(default_factory=list)
    panels: list[str] = Field(default_factory=list)
    allow_from: list[str] = Field(default_factory=list)
    mention: MochatMentionConfig = Field(default_factory=MochatMentionConfig)
    groups: dict[str, MochatGroupRule] = Field(default_factory=dict)
    reply_delay_mode: str = "non-mention"  # off | non-mention
    reply_delay_ms: int = 120000


class SlackDMConfig(BaseModel):
    """Slack DM policy configuration."""
    enabled: bool = True
    policy: str = "open"  # "open" or "allowlist"
    allow_from: list[str] = Field(default_factory=list)  # Allowed Slack user IDs


class SlackConfig(BaseModel):
    """Slack channel configuration."""
    enabled: bool = False
    mode: str = "socket"  # "socket" supported
    webhook_path: str = "/slack/events"
    bot_token: str = ""  # xoxb-...
    app_token: str = ""  # xapp-...
    user_token_read_only: bool = True
    group_policy: str = "mention"  # "mention", "open", "allowlist"
    group_allow_from: list[str] = Field(default_factory=list)  # Allowed channel IDs if allowlist
    dm: SlackDMConfig = Field(default_factory=SlackDMConfig)


class QQConfig(BaseModel):
    """QQ channel configuration using botpy SDK."""
    enabled: bool = False
    app_id: str = ""  # 机器人 ID (AppID) from q.qq.com
    secret: str = ""  # 机器人密钥 (AppSecret) from q.qq.com
    allow_from: list[str] = Field(default_factory=list)  # Allowed user openids (empty = public access)


class ChannelsConfig(BaseModel):
    """聊天渠道配置集合。"""
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    feishu: FeishuConfig = Field(default_factory=FeishuConfig)
    mochat: MochatConfig = Field(default_factory=MochatConfig)
    dingtalk: DingTalkConfig = Field(default_factory=DingTalkConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    qq: QQConfig = Field(default_factory=QQConfig)


class AgentDefaults(BaseModel):
    """智能体默认配置。"""
    workspace: str = "~/.nanobot/workspace"  # 工作空间路径
    model: str = "anthropic/claude-opus-4-5"  # 默认模型
    max_tokens: int = 8192  # 最大token数
    temperature: float = 0.7  # 温度参数
    max_tool_iterations: int = 20  # 最大工具调用迭代次数


class AgentsConfig(BaseModel):
    """智能体配置。"""
    defaults: AgentDefaults = Field(default_factory=AgentDefaults)


class ProviderConfig(BaseModel):
    """LLM提供者配置。"""
    api_key: str = ""  # API密钥
    api_base: str | None = None  # API基础URL（可选）
    extra_headers: dict[str, str] | None = None  # 自定义请求头（例如AiHubMix的APP-Code）


class ProvidersConfig(BaseModel):
    """LLM提供者配置集合。"""
    anthropic: ProviderConfig = Field(default_factory=ProviderConfig)  # Anthropic (Claude)
    openai: ProviderConfig = Field(default_factory=ProviderConfig)  # OpenAI
    openrouter: ProviderConfig = Field(default_factory=ProviderConfig)  # OpenRouter
    deepseek: ProviderConfig = Field(default_factory=ProviderConfig)  # DeepSeek
    groq: ProviderConfig = Field(default_factory=ProviderConfig)  # Groq
    zhipu: ProviderConfig = Field(default_factory=ProviderConfig)  # 智谱AI
    dashscope: ProviderConfig = Field(default_factory=ProviderConfig)  # 阿里云通义千问
    vllm: ProviderConfig = Field(default_factory=ProviderConfig)  # vLLM
    gemini: ProviderConfig = Field(default_factory=ProviderConfig)  # Google Gemini
    moonshot: ProviderConfig = Field(default_factory=ProviderConfig)  # Moonshot
    minimax: ProviderConfig = Field(default_factory=ProviderConfig)  # MiniMax
    aihubmix: ProviderConfig = Field(default_factory=ProviderConfig)  # AiHubMix API网关


class GatewayConfig(BaseModel):
    """网关/服务器配置。"""
    host: str = "0.0.0.0"  # 监听地址
    port: int = 18790  # 监听端口


class ProxyConfig(BaseModel):
    """全局代理配置（可选，用于环境变量等场景）。"""
    https_proxy: str | None = None
    http_proxy: str | None = None
    all_proxy: str | None = None


class WebSearchConfig(BaseModel):
    """网络搜索工具配置。"""
    api_key: str = ""  # Brave Search API密钥
    max_results: int = 5  # 最大搜索结果数


class WebToolsConfig(BaseModel):
    """网络工具配置。"""
    search: WebSearchConfig = Field(default_factory=WebSearchConfig)


class ExecToolConfig(BaseModel):
    """Shell执行工具配置。"""
    timeout: int = 60  # 命令执行超时时间（秒）


class ToolsConfig(BaseModel):
    """工具配置。"""
    web: WebToolsConfig = Field(default_factory=WebToolsConfig)  # 网络工具配置
    exec: ExecToolConfig = Field(default_factory=ExecToolConfig)  # Shell执行工具配置
    restrict_to_workspace: bool = False  # 如果为True，限制所有工具访问工作空间目录


class Config(BaseSettings):
    """
    nanobot的根配置类。
    
    包含所有配置项，包括智能体、渠道、提供者、网关和工具配置。
    支持从环境变量加载配置（通过NANOBOT_前缀）。
    """
    agents: AgentsConfig = Field(default_factory=AgentsConfig)  # 智能体配置
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)  # 渠道配置
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)  # 提供者配置
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)  # 网关配置
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)  # 全局代理（可选）
    tools: ToolsConfig = Field(default_factory=ToolsConfig)  # 工具配置
    
    @property
    def workspace_path(self) -> Path:
        """
        获取展开后的工作空间路径。
        
        Returns:
            工作空间路径
        """
        return Path(self.agents.defaults.workspace).expanduser()
    
    def _match_provider(self, model: str | None = None) -> tuple["ProviderConfig | None", str | None]:
        """
        匹配提供者配置及其注册表名称。
        
        根据模型名称的关键词匹配相应的提供者配置。
        如果无法匹配，则回退到第一个可用的提供者。
        
        Args:
            model: 模型名称，如果为None则使用默认模型
        
        Returns:
            包含(配置对象, 提供者名称)的元组
        """
        from nanobot.providers.registry import PROVIDERS
        model_lower = (model or self.agents.defaults.model).lower()

        # 按关键词匹配（顺序遵循PROVIDERS注册表）
        for spec in PROVIDERS:
            p = getattr(self.providers, spec.name, None)
            if p and any(kw in model_lower for kw in spec.keywords) and p.api_key:
                return p, spec.name

        # 回退：先网关，后其他（遵循注册表顺序）
        for spec in PROVIDERS:
            p = getattr(self.providers, spec.name, None)
            if p and p.api_key:
                return p, spec.name
        return None, None

    def get_provider(self, model: str | None = None) -> ProviderConfig | None:
        """
        获取匹配的提供者配置（api_key, api_base, extra_headers）。
        
        如果无法匹配，则回退到第一个可用的提供者。
        
        Args:
            model: 模型名称，如果为None则使用默认模型
        
        Returns:
            提供者配置对象，如果未找到则返回None
        """
        p, _ = self._match_provider(model)
        return p

    def get_provider_name(self, model: str | None = None) -> str | None:
        """
        获取匹配的提供者的注册表名称。
        
        例如："deepseek"、"openrouter"等。
        
        Args:
            model: 模型名称，如果为None则使用默认模型
        
        Returns:
            提供者名称，如果未找到则返回None
        """
        _, name = self._match_provider(model)
        return name

    def get_api_key(self, model: str | None = None) -> str | None:
        """
        获取指定模型的API密钥。
        
        如果无法匹配，则回退到第一个可用的密钥。
        
        Args:
            model: 模型名称，如果为None则使用默认模型
        
        Returns:
            API密钥，如果未找到则返回None
        """
        p = self.get_provider(model)
        return p.api_key if p else None
    
    def get_api_base(self, model: str | None = None) -> str | None:
        """
        获取指定模型的API基础URL。
        
        为已知的网关应用默认URL。只有网关会在这里获得默认api_base。
        标准提供者（如Moonshot）通过环境变量在_setup_env中设置其基础URL，
        以避免污染全局的litellm.api_base。
        
        Args:
            model: 模型名称，如果为None则使用默认模型
        
        Returns:
            API基础URL，如果未找到则返回None
        """
        from nanobot.providers.registry import find_by_name
        p, name = self._match_provider(model)
        if p and p.api_base:
            return p.api_base
        # 只有网关会在这里获得默认api_base。标准提供者
        # （如Moonshot）通过环境变量在_setup_env中设置其基础URL，
        # 以避免污染全局的litellm.api_base。
        if name:
            spec = find_by_name(name)
            if spec and spec.is_gateway and spec.default_api_base:
                return spec.default_api_base
        return None
    
    model_config = ConfigDict(
        env_prefix="NANOBOT_",
        env_nested_delimiter="__"
    )
