"""nanobot配置模块。

此模块提供了配置文件的加载、保存和模式定义功能。
"""

from nanobot.config.loader import load_config, get_config_path
from nanobot.config.schema import Config

__all__ = ["Config", "load_config", "get_config_path"]
