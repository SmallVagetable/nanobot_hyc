"""
本地直接启动 nanobot 的入口脚本。

用法示例（在项目根目录运行）：

    python run.py agent -m "你好"
    python run.py gateway
"""

from nanobot.cli.commands import app


if __name__ == "__main__":
    app()

