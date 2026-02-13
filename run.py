"""
本地直接启动 nanobot 的入口脚本。

用法示例（在项目根目录运行）：

    python run.py agent -m "你好"
    python run.py gateway
    python run.py cron add -n "每日加密货币涨跌幅" -m "请查询当前比特币(BTC)和以太坊(ETH)的涨跌幅，并分别给出过去1小时和24小时的涨跌幅数据，用简洁清晰的格式回复。" -c "0 9,12,15,18,21 * * *" -d --to "1468646207302668565" --channel "discord"
    python run.py cron add -n "每日天气预报" -m "请查询北京和杭州的天气预报，用简洁清晰的格式回复。" -c "0 9 * * *" -d --to "1468646207302668565" --channel "discord"
"""

from nanobot.cli.commands import app


if __name__ == "__main__":
    app()

