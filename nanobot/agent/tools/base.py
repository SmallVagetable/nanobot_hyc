"""智能体工具的基础类。

此模块定义了工具系统的抽象基类，所有工具都必须继承自Tool类。
工具是智能体用于与环境交互的能力，例如读取文件、执行命令等。
"""

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """
    智能体工具的抽象基类。
    
    工具是智能体用于与环境交互的能力，例如：
    - 读取、写入、编辑文件
    - 执行Shell命令
    - 搜索网络
    - 发送消息
    - 生成子智能体等
    
    所有工具都必须实现name、description、parameters和execute方法。
    """
    
    # 类型映射表，用于参数验证
    _TYPE_MAP = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        工具名称，用于函数调用。
        
        Returns:
            工具名称字符串
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        工具描述，说明工具的功能。
        
        Returns:
            工具描述字符串
        """
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """
        工具参数的JSON Schema定义。
        
        Returns:
            JSON Schema字典，定义工具的参数结构
        """
        pass
    
    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """
        使用给定参数执行工具。
        
        Args:
            **kwargs: 工具特定的参数
        
        Returns:
            工具执行结果的字符串表示
        """
        pass

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """
        根据JSON Schema验证工具参数。
        
        Args:
            params: 要验证的参数字典
        
        Returns:
            错误列表，如果验证通过则返回空列表
        """
        schema = self.parameters or {}
        if schema.get("type", "object") != "object":
            raise ValueError(f"Schema must be object type, got {schema.get('type')!r}")
        return self._validate(params, {**schema, "type": "object"}, "")

    def _validate(self, val: Any, schema: dict[str, Any], path: str) -> list[str]:
        """
        递归验证值是否符合Schema定义。
        
        Args:
            val: 要验证的值
            schema: JSON Schema定义
            path: 当前验证路径（用于错误报告）
        
        Returns:
            错误列表
        """
        t, label = schema.get("type"), path or "parameter"
        if t in self._TYPE_MAP and not isinstance(val, self._TYPE_MAP[t]):
            return [f"{label} should be {t}"]
        
        errors = []
        # 枚举值验证
        if "enum" in schema and val not in schema["enum"]:
            errors.append(f"{label} must be one of {schema['enum']}")
        # 数值范围验证
        if t in ("integer", "number"):
            if "minimum" in schema and val < schema["minimum"]:
                errors.append(f"{label} must be >= {schema['minimum']}")
            if "maximum" in schema and val > schema["maximum"]:
                errors.append(f"{label} must be <= {schema['maximum']}")
        # 字符串长度验证
        if t == "string":
            if "minLength" in schema and len(val) < schema["minLength"]:
                errors.append(f"{label} must be at least {schema['minLength']} chars")
            if "maxLength" in schema and len(val) > schema["maxLength"]:
                errors.append(f"{label} must be at most {schema['maxLength']} chars")
        # 对象属性验证
        if t == "object":
            props = schema.get("properties", {})
            # 检查必需属性
            for k in schema.get("required", []):
                if k not in val:
                    errors.append(f"missing required {path + '.' + k if path else k}")
            # 验证每个属性
            for k, v in val.items():
                if k in props:
                    errors.extend(self._validate(v, props[k], path + '.' + k if path else k))
        # 数组元素验证
        if t == "array" and "items" in schema:
            for i, item in enumerate(val):
                errors.extend(self._validate(item, schema["items"], f"{path}[{i}]" if path else f"[{i}]"))
        return errors
    
    def to_schema(self) -> dict[str, Any]:
        """
        将工具转换为OpenAI函数模式格式。
        
        用于将工具定义转换为LLM可以理解的函数调用格式。
        
        Returns:
            OpenAI函数模式字典
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }
