"""
nanobot模块的入口点

当使用 `python -m nanobot` 命令运行nanobot时，会执行此文件。
它导入并启动CLI应用程序。
"""

from nanobot.cli.commands import app

if __name__ == "__main__":
    app()
