"""工具注册表，用于动态工具管理。

此模块实现了工具注册表，用于管理所有可用的工具。
支持动态注册、注销和执行工具。
"""

from typing import Any

from nanobot.agent.tools.base import Tool


class ToolRegistry:
    """
    智能体工具注册表。
    
    用于管理所有可用的工具，支持：
    - 动态注册和注销工具
    - 根据名称获取工具
    - 执行工具并验证参数
    - 获取所有工具的定义（用于LLM）
    """
    
    def __init__(self):
        """初始化工具注册表。"""
        self._tools: dict[str, Tool] = {}  # 工具字典，键为工具名称
    
    def register(self, tool: Tool) -> None:
        """
        注册一个工具。
        
        Args:
            tool: 要注册的工具对象
        """
        self._tools[tool.name] = tool
    
    def unregister(self, name: str) -> None:
        """
        根据名称注销工具。
        
        Args:
            name: 工具名称
        """
        self._tools.pop(name, None)
    
    def get(self, name: str) -> Tool | None:
        """
        根据名称获取工具。
        
        Args:
            name: 工具名称
        
        Returns:
            工具对象，如果未找到则返回None
        """
        return self._tools.get(name)
    
    def has(self, name: str) -> bool:
        """
        检查工具是否已注册。
        
        Args:
            name: 工具名称
        
        Returns:
            如果工具已注册返回True，否则返回False
        """
        return name in self._tools
    
    def get_definitions(self) -> list[dict[str, Any]]:
        """
        获取所有工具的定义（OpenAI格式）。
        
        用于将工具定义传递给LLM，使其知道可以调用哪些工具。
        
        Returns:
            工具定义列表，每个定义都是OpenAI函数模式格式
        """
        return [tool.to_schema() for tool in self._tools.values()]
    
    async def execute(self, name: str, params: dict[str, Any]) -> str:
        """
        根据名称和参数执行工具。
        
        执行前会先验证参数是否符合工具的定义。
        如果验证失败或执行出错，会返回错误信息。
        
        Args:
            name: 工具名称
            params: 工具参数字典
        
        Returns:
            工具执行结果的字符串表示
        
        Raises:
            KeyError: 如果工具未找到（但会返回错误字符串而不是抛出异常）
        """
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"

        try:
            # 验证参数
            errors = tool.validate_params(params)
            if errors:
                return f"Error: Invalid parameters for tool '{name}': " + "; ".join(errors)
            # 执行工具
            return await tool.execute(**params)
        except Exception as e:
            return f"Error executing {name}: {str(e)}"
    
    @property
    def tool_names(self) -> list[str]:
        """
        获取所有已注册工具的名称列表。
        
        Returns:
            工具名称列表
        """
        return list(self._tools.keys())
    
    def __len__(self) -> int:
        """返回已注册工具的数量。"""
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        """检查工具是否已注册（支持in操作符）。"""
        return name in self._tools
