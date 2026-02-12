"""使用LiteLLM实现的多提供者支持。

此模块实现了基于LiteLLM的LLM提供者，支持通过统一接口
访问多个LLM提供者（OpenRouter、Anthropic、OpenAI、Gemini、MiniMax等）。
提供者特定的逻辑由注册表驱动（参见providers/registry.py），
无需在此处使用if-elif链。
"""

import json
import os
from typing import Any

import litellm
from litellm import acompletion

from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest
from nanobot.providers.registry import find_by_model, find_gateway


class LiteLLMProvider(LLMProvider):
    """
    使用LiteLLM实现的多提供者LLM提供者。
    
    通过统一接口支持OpenRouter、Anthropic、OpenAI、Gemini、MiniMax等
    多个提供者。提供者特定的逻辑由注册表驱动（参见providers/registry.py），
    无需在此处使用if-elif链。
    
    支持的功能：
    - 自动检测网关和本地部署
    - 自动添加模型前缀
    - 模型特定的参数覆盖
    - 工具调用支持
    - 推理内容支持（用于支持思考过程的模型）
    """
    
    def __init__(
        self, 
        api_key: str | None = None, 
        api_base: str | None = None,
        default_model: str = "anthropic/claude-opus-4-5",
        extra_headers: dict[str, str] | None = None,
        provider_name: str | None = None,
    ):
        super().__init__(api_key, api_base)
        self.default_model = default_model
        self.extra_headers = extra_headers or {}
        
        # Detect gateway / local deployment.
        # provider_name (from config key) is the primary signal;
        # api_key / api_base are fallback for auto-detection.
        self._gateway = find_gateway(provider_name, api_key, api_base)
        
        # Configure environment variables
        if api_key:
            self._setup_env(api_key, api_base, default_model)
        
        if api_base:
            litellm.api_base = api_base
        
        # Disable LiteLLM logging noise
        litellm.suppress_debug_info = True
        # Drop unsupported parameters for providers (e.g., gpt-5 rejects some params)
        litellm.drop_params = True
    
    def _setup_env(self, api_key: str, api_base: str | None, model: str) -> None:
        """
        根据检测到的提供者设置环境变量。
        
        设置LiteLLM所需的环境变量，包括API密钥和额外的环境变量。
        对于网关/本地部署，会覆盖现有环境变量；对于标准提供者，只设置默认值。
        
        Args:
            api_key: API密钥
            api_base: API基础URL
            model: 模型名称
        """
        spec = self._gateway or find_by_model(model)
        if not spec:
            return

        # 网关/本地部署覆盖现有环境变量；标准提供者不覆盖
        if self._gateway:
            os.environ[spec.env_key] = api_key
        else:
            os.environ.setdefault(spec.env_key, api_key)

        # 解析env_extras占位符：
        #   {api_key}  → 用户的API密钥
        #   {api_base} → 用户的api_base，回退到spec.default_api_base
        effective_base = api_base or spec.default_api_base
        for env_name, env_val in spec.env_extras:
            resolved = env_val.replace("{api_key}", api_key)
            resolved = resolved.replace("{api_base}", effective_base)
            os.environ.setdefault(env_name, resolved)
    
    def _resolve_model(self, model: str) -> str:
        """
        通过应用提供者/网关前缀来解析模型名称。
        
        根据检测到的提供者或网关，自动添加相应的前缀。
        例如：claude-3 → anthropic/claude-3（如果使用标准提供者）
             或 openrouter/claude-3（如果使用OpenRouter网关）
        
        Args:
            model: 原始模型名称
        
        Returns:
            解析后的模型名称（带前缀）
        """
        if self._gateway:
            # 网关模式：应用网关前缀，跳过提供者特定前缀
            prefix = self._gateway.litellm_prefix
            if self._gateway.strip_model_prefix:
                # 剥离现有前缀（例如：anthropic/claude-3 → claude-3）
                model = model.split("/")[-1]
            if prefix and not model.startswith(f"{prefix}/"):
                model = f"{prefix}/{model}"
            return model
        
        # 标准模式：为已知提供者自动添加前缀
        spec = find_by_model(model)
        if spec and spec.litellm_prefix:
            if not any(model.startswith(s) for s in spec.skip_prefixes):
                model = f"{spec.litellm_prefix}/{model}"
        
        return model
    
    def _apply_model_overrides(self, model: str, kwargs: dict[str, Any]) -> None:
        """
        应用注册表中的模型特定参数覆盖。
        
        某些模型可能需要特定的参数设置（例如kimi-k2.5要求temperature >= 1.0），
        此方法会根据模型名称应用这些覆盖。
        
        Args:
            model: 模型名称
            kwargs: 要传递给API的参数字典
        """
        model_lower = model.lower()
        spec = find_by_model(model)
        if spec:
            for pattern, overrides in spec.model_overrides:
                if pattern in model_lower:
                    kwargs.update(overrides)
                    return
    
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Send a chat completion request via LiteLLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            tools: Optional list of tool definitions in OpenAI format.
            model: Model identifier (e.g., 'anthropic/claude-sonnet-4-5').
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.
        
        Returns:
            LLMResponse with content and/or tool calls.
        """
        model = self._resolve_model(model or self.default_model)
        
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # Apply model-specific overrides (e.g. kimi-k2.5 temperature)
        self._apply_model_overrides(model, kwargs)
        
        # Pass api_key directly — more reliable than env vars alone
        if self.api_key:
            kwargs["api_key"] = self.api_key
        
        # Pass api_base for custom endpoints
        if self.api_base:
            kwargs["api_base"] = self.api_base
        
        # Pass extra headers (e.g. APP-Code for AiHubMix)
        if self.extra_headers:
            kwargs["extra_headers"] = self.extra_headers
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        try:
            response = await acompletion(**kwargs)
            return self._parse_response(response)
        except Exception as e:
            # Return error as content for graceful handling
            return LLMResponse(
                content=f"Error calling LLM: {str(e)}",
                finish_reason="error",
            )
    
    def _parse_response(self, response: Any) -> LLMResponse:
        """
        将LiteLLM响应解析为我们的标准格式。
        
        从LiteLLM的响应对象中提取内容、工具调用、使用统计等信息，
        并转换为标准的LLMResponse格式。
        
        Args:
            response: LiteLLM的响应对象
        
        Returns:
            标准化的LLMResponse对象
        """
        choice = response.choices[0]
        message = choice.message
        
        tool_calls = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                # 如果需要，从JSON字符串解析参数
                args = tc.function.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw": args}
                
                tool_calls.append(ToolCallRequest(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))
        
        usage = {}
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        
        reasoning_content = getattr(message, "reasoning_content", None)
        
        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
            reasoning_content=reasoning_content,
        )
    
    def get_default_model(self) -> str:
        """
        获取默认模型。
        
        Returns:
            默认模型名称
        """
        return self.default_model
