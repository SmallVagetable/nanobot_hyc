"""配置加载工具。

此模块提供了配置文件的加载、保存和格式转换功能。
配置文件使用JSON格式，键名使用camelCase（与前端保持一致），
但在Python代码中使用snake_case（符合Pydantic规范）。
"""

import json
from pathlib import Path
from typing import Any

from nanobot.config.schema import Config


def get_config_path() -> Path:
    """
    获取默认配置文件路径。
    
    Returns:
        配置文件路径（~/.nanobot/config.json）
    """
    return Path.home() / ".nanobot" / "config.json"


def get_data_dir() -> Path:
    """
    获取nanobot数据目录路径。
    
    Returns:
        数据目录路径
    """
    from nanobot.utils.helpers import get_data_path
    return get_data_path()


def load_config(config_path: Path | None = None) -> Config:
    """
    从文件加载配置或创建默认配置。
    
    如果配置文件不存在或加载失败，会返回默认配置对象。
    加载时会自动进行配置迁移（将旧格式转换为新格式）和
    键名转换（camelCase转snake_case）。
    
    Args:
        config_path: 可选的配置文件路径，如果未提供则使用默认路径
    
    Returns:
        加载的配置对象
    """
    path = config_path or get_config_path()
    
    if path.exists():
        try:
            with open(path) as f:
                data = json.load(f)
            data = _migrate_config(data)
            return Config.model_validate(convert_keys(data))
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to load config from {path}: {e}")
            print("Using default configuration.")
    
    return Config()


def save_config(config: Config, config_path: Path | None = None) -> None:
    """
    保存配置到文件。
    
    保存前会将snake_case键名转换为camelCase，以保持与前端的一致性。
    
    Args:
        config: 要保存的配置对象
        config_path: 可选的保存路径，如果未提供则使用默认路径
    """
    path = config_path or get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 转换为camelCase格式
    data = config.model_dump()
    data = convert_to_camel(data)
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _migrate_config(data: dict) -> dict:
    """
    迁移旧配置格式到当前格式。
    
    处理配置格式的向后兼容性，将旧版本的配置结构转换为新版本。
    例如：将tools.exec.restrictToWorkspace移动到tools.restrictToWorkspace。
    
    Args:
        data: 配置数据字典
    
    Returns:
        迁移后的配置数据
    """
    # 将tools.exec.restrictToWorkspace移动到tools.restrictToWorkspace
    tools = data.get("tools", {})
    exec_cfg = tools.get("exec", {})
    if "restrictToWorkspace" in exec_cfg and "restrictToWorkspace" not in tools:
        tools["restrictToWorkspace"] = exec_cfg.pop("restrictToWorkspace")
    return data


def convert_keys(data: Any) -> Any:
    """
    将camelCase键名转换为snake_case（用于Pydantic）。
    
    递归处理字典和列表，将所有键名从camelCase转换为snake_case。
    
    Args:
        data: 要转换的数据（可以是字典、列表或其他类型）
    
    Returns:
        转换后的数据
    """
    if isinstance(data, dict):
        return {camel_to_snake(k): convert_keys(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_keys(item) for item in data]
    return data


def convert_to_camel(data: Any) -> Any:
    """
    将snake_case键名转换为camelCase。
    
    递归处理字典和列表，将所有键名从snake_case转换为camelCase。
    用于保存配置时保持与前端的一致性。
    
    Args:
        data: 要转换的数据（可以是字典、列表或其他类型）
    
    Returns:
        转换后的数据
    """
    if isinstance(data, dict):
        return {snake_to_camel(k): convert_to_camel(v) for k, v in data.items()}
    if isinstance(data, list):
        return [convert_to_camel(item) for item in data]
    return data


def camel_to_snake(name: str) -> str:
    """
    将camelCase转换为snake_case。
    
    例如：restrictToWorkspace -> restrict_to_workspace
    
    Args:
        name: camelCase字符串
    
    Returns:
        snake_case字符串
    """
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


def snake_to_camel(name: str) -> str:
    """
    将snake_case转换为camelCase。
    
    例如：restrict_to_workspace -> restrictToWorkspace
    
    Args:
        name: snake_case字符串
    
    Returns:
        camelCase字符串
    """
    components = name.split("_")
    return components[0] + "".join(x.title() for x in components[1:])
