"""
提供者注册表 — LLM提供者元数据的单一真实来源。

添加新提供者的步骤：
  1. 在下面的PROVIDERS中添加一个ProviderSpec。
  2. 在config/schema.py的ProvidersConfig中添加一个字段。
  完成。环境变量、前缀、配置匹配、状态显示都从这里派生。

顺序很重要 — 它控制匹配优先级和回退顺序。网关优先。
每个条目都写出所有字段，以便您可以复制粘贴作为模板。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderSpec:
    """
    一个LLM提供者的元数据。参见下面的PROVIDERS了解真实示例。

    env_extras值中的占位符：
      {api_key}  — 用户的API密钥
      {api_base} — 来自配置的api_base，或此规范的default_api_base
    """

    # 身份信息
    name: str  # 配置字段名称，例如"dashscope"
    keywords: tuple[str, ...]  # 用于匹配的模型名称关键词（小写）
    env_key: str  # LiteLLM环境变量，例如"DASHSCOPE_API_KEY"
    display_name: str = ""  # 在`nanobot status`中显示的名称

    # 模型前缀
    litellm_prefix: str = ""  # "dashscope" → 模型变为"dashscope/{model}"
    skip_prefixes: tuple[str, ...] = ()  # 如果模型已以这些前缀开头，则不添加前缀

    # 额外的环境变量，例如(("ZHIPUAI_API_KEY", "{api_key}"),)
    env_extras: tuple[tuple[str, str], ...] = ()

    # 网关/本地检测
    is_gateway: bool = False  # 路由任何模型（OpenRouter、AiHubMix）
    is_local: bool = False  # 本地部署（vLLM、Ollama）
    detect_by_key_prefix: str = ""  # 匹配api_key前缀，例如"sk-or-"
    detect_by_base_keyword: str = ""  # 匹配api_base URL中的子字符串
    default_api_base: str = ""  # 回退基础URL

    # 网关行为
    strip_model_prefix: bool = False  # 在重新添加前缀之前剥离"provider/"

    # 每个模型的参数覆盖，例如(("kimi-k2.5", {"temperature": 1.0}),)
    model_overrides: tuple[tuple[str, dict[str, Any]], ...] = ()

    @property
    def label(self) -> str:
        """
        获取显示标签。
        
        Returns:
            显示名称，如果没有则返回首字母大写的名称
        """
        return self.display_name or self.name.title()


# ---------------------------------------------------------------------------
# PROVIDERS — 注册表。顺序 = 优先级。复制任何条目作为模板。
# ---------------------------------------------------------------------------

PROVIDERS: tuple[ProviderSpec, ...] = (

    # === 网关（通过api_key / api_base检测，而非模型名称）=========
    # 网关可以路由任何模型，因此在回退时优先。

    # OpenRouter: global gateway, keys start with "sk-or-"
    ProviderSpec(
        name="openrouter",
        keywords=("openrouter",),
        env_key="OPENROUTER_API_KEY",
        display_name="OpenRouter",
        litellm_prefix="openrouter",        # claude-3 → openrouter/claude-3
        skip_prefixes=(),
        env_extras=(),
        is_gateway=True,
        is_local=False,
        detect_by_key_prefix="sk-or-",
        detect_by_base_keyword="openrouter",
        default_api_base="https://openrouter.ai/api/v1",
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # AiHubMix: global gateway, OpenAI-compatible interface.
    # strip_model_prefix=True: it doesn't understand "anthropic/claude-3",
    # so we strip to bare "claude-3" then re-prefix as "openai/claude-3".
    ProviderSpec(
        name="aihubmix",
        keywords=("aihubmix",),
        env_key="OPENAI_API_KEY",           # OpenAI-compatible
        display_name="AiHubMix",
        litellm_prefix="openai",            # → openai/{model}
        skip_prefixes=(),
        env_extras=(),
        is_gateway=True,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="aihubmix",
        default_api_base="https://aihubmix.com/v1",
        strip_model_prefix=True,            # anthropic/claude-3 → claude-3 → openai/claude-3
        model_overrides=(),
    ),

    # === 标准提供者（通过模型名称关键词匹配）===============

    # Anthropic: LiteLLM recognizes "claude-*" natively, no prefix needed.
    ProviderSpec(
        name="anthropic",
        keywords=("anthropic", "claude"),
        env_key="ANTHROPIC_API_KEY",
        display_name="Anthropic",
        litellm_prefix="",
        skip_prefixes=(),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # OpenAI: LiteLLM recognizes "gpt-*" natively, no prefix needed.
    ProviderSpec(
        name="openai",
        keywords=("openai", "gpt"),
        env_key="OPENAI_API_KEY",
        display_name="OpenAI",
        litellm_prefix="",
        skip_prefixes=(),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # DeepSeek: needs "deepseek/" prefix for LiteLLM routing.
    ProviderSpec(
        name="deepseek",
        keywords=("deepseek",),
        env_key="DEEPSEEK_API_KEY",
        display_name="DeepSeek",
        litellm_prefix="deepseek",          # deepseek-chat → deepseek/deepseek-chat
        skip_prefixes=("deepseek/",),       # avoid double-prefix
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # Gemini: needs "gemini/" prefix for LiteLLM.
    ProviderSpec(
        name="gemini",
        keywords=("gemini",),
        env_key="GEMINI_API_KEY",
        display_name="Gemini",
        litellm_prefix="gemini",            # gemini-pro → gemini/gemini-pro
        skip_prefixes=("gemini/",),         # avoid double-prefix
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # Zhipu: LiteLLM uses "zai/" prefix.
    # Also mirrors key to ZHIPUAI_API_KEY (some LiteLLM paths check that).
    # skip_prefixes: don't add "zai/" when already routed via gateway.
    ProviderSpec(
        name="zhipu",
        keywords=("zhipu", "glm", "zai"),
        env_key="ZAI_API_KEY",
        display_name="Zhipu AI",
        litellm_prefix="zai",              # glm-4 → zai/glm-4
        skip_prefixes=("zhipu/", "zai/", "openrouter/", "hosted_vllm/"),
        env_extras=(
            ("ZHIPUAI_API_KEY", "{api_key}"),
        ),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # DashScope: Qwen models, needs "dashscope/" prefix.
    ProviderSpec(
        name="dashscope",
        keywords=("qwen", "dashscope"),
        env_key="DASHSCOPE_API_KEY",
        display_name="DashScope",
        litellm_prefix="dashscope",         # qwen-max → dashscope/qwen-max
        skip_prefixes=("dashscope/", "openrouter/"),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # Moonshot: Kimi models, needs "moonshot/" prefix.
    # LiteLLM requires MOONSHOT_API_BASE env var to find the endpoint.
    # Kimi K2.5 API enforces temperature >= 1.0.
    ProviderSpec(
        name="moonshot",
        keywords=("moonshot", "kimi"),
        env_key="MOONSHOT_API_KEY",
        display_name="Moonshot",
        litellm_prefix="moonshot",          # kimi-k2.5 → moonshot/kimi-k2.5
        skip_prefixes=("moonshot/", "openrouter/"),
        env_extras=(
            ("MOONSHOT_API_BASE", "{api_base}"),
        ),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="https://api.moonshot.ai/v1",   # intl; use api.moonshot.cn for China
        strip_model_prefix=False,
        model_overrides=(
            ("kimi-k2.5", {"temperature": 1.0}),
        ),
    ),

    # MiniMax: needs "minimax/" prefix for LiteLLM routing.
    # Uses OpenAI-compatible API at api.minimax.io/v1.
    ProviderSpec(
        name="minimax",
        keywords=("minimax",),
        env_key="MINIMAX_API_KEY",
        display_name="MiniMax",
        litellm_prefix="minimax",            # MiniMax-M2.1 → minimax/MiniMax-M2.1
        skip_prefixes=("minimax/", "openrouter/"),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="https://api.minimax.io/v1",
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # === 本地部署（通过配置键匹配，而非api_base）=========

    # vLLM / any OpenAI-compatible local server.
    # Detected when config key is "vllm" (provider_name="vllm").
    ProviderSpec(
        name="vllm",
        keywords=("vllm",),
        env_key="HOSTED_VLLM_API_KEY",
        display_name="vLLM/Local",
        litellm_prefix="hosted_vllm",      # Llama-3-8B → hosted_vllm/Llama-3-8B
        skip_prefixes=(),
        env_extras=(),
        is_gateway=False,
        is_local=True,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",                # user must provide in config
        strip_model_prefix=False,
        model_overrides=(),
    ),

    # === 辅助提供者（非主要LLM提供者）============================

    # Groq: mainly used for Whisper voice transcription, also usable for LLM.
    # Needs "groq/" prefix for LiteLLM routing. Placed last — it rarely wins fallback.
    ProviderSpec(
        name="groq",
        keywords=("groq",),
        env_key="GROQ_API_KEY",
        display_name="Groq",
        litellm_prefix="groq",              # llama3-8b-8192 → groq/llama3-8b-8192
        skip_prefixes=("groq/",),           # avoid double-prefix
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="",
        detect_by_base_keyword="",
        default_api_base="",
        strip_model_prefix=False,
        model_overrides=(),
    ),
)


# ---------------------------------------------------------------------------
# 查找辅助函数
# ---------------------------------------------------------------------------

def find_by_model(model: str) -> ProviderSpec | None:
    """
    通过模型名称关键词匹配标准提供者（不区分大小写）。
    
    跳过网关/本地提供者 — 这些通过api_key/api_base匹配。
    
    Args:
        model: 模型名称
    
    Returns:
        匹配的ProviderSpec，如果未找到则返回None
    """
    model_lower = model.lower()
    for spec in PROVIDERS:
        if spec.is_gateway or spec.is_local:
            continue
        if any(kw in model_lower for kw in spec.keywords):
            return spec
    return None


def find_gateway(
    provider_name: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
) -> ProviderSpec | None:
    """
    检测网关/本地提供者。

    优先级：
      1. provider_name — 如果它映射到网关/本地规范，直接使用。
      2. api_key前缀 — 例如"sk-or-" → OpenRouter。
      3. api_base关键词 — 例如URL中的"aihubmix" → AiHubMix。

    具有自定义api_base的标准提供者（例如代理后的DeepSeek）
    不会被误认为是vLLM — 旧的回退已移除。
    
    Args:
        provider_name: 提供者名称
        api_key: API密钥
        api_base: API基础URL
    
    Returns:
        匹配的ProviderSpec，如果未找到则返回None
    """
    # 1. 通过配置键直接匹配
    if provider_name:
        spec = find_by_name(provider_name)
        if spec and (spec.is_gateway or spec.is_local):
            return spec

    # 2. 通过api_key前缀/api_base关键词自动检测
    for spec in PROVIDERS:
        if spec.detect_by_key_prefix and api_key and api_key.startswith(spec.detect_by_key_prefix):
            return spec
        if spec.detect_by_base_keyword and api_base and spec.detect_by_base_keyword in api_base:
            return spec

    return None


def find_by_name(name: str) -> ProviderSpec | None:
    """
    通过配置字段名称查找提供者规范。
    
    例如："dashscope"
    
    Args:
        name: 提供者名称
    
    Returns:
        匹配的ProviderSpec，如果未找到则返回None
    """
    for spec in PROVIDERS:
        if spec.name == name:
            return spec
    return None
