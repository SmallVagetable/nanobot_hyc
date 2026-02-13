#!/bin/bash

# 停止 nanobot gateway 服务的脚本

echo "正在查找 gateway 进程..."

# 方法1: 通过进程名查找并停止
PID=$(pgrep -f "run.py gateway" | head -1)

if [ -z "$PID" ]; then
    # 方法2: 通过端口号查找
    PID=$(lsof -ti:18790 2>/dev/null | head -1)
fi

if [ -z "$PID" ]; then
    # 方法3: 通过 Python 进程和 gateway 关键词查找
    PID=$(ps aux | grep -i "python.*gateway\|gateway.*python" | grep -v grep | awk '{print $2}' | head -1)
fi

if [ -n "$PID" ]; then
    echo "找到进程 PID: $PID"
    echo "正在停止进程..."
    kill $PID
    
    # 等待进程结束
    sleep 2
    
    # 检查进程是否还在运行
    if ps -p $PID > /dev/null 2>&1; then
        echo "进程仍在运行，强制停止..."
        kill -9 $PID
        sleep 1
    fi
    
    if ! ps -p $PID > /dev/null 2>&1; then
        echo "✓ Gateway 服务已成功停止"
    else
        echo "✗ 停止失败，请手动检查"
    fi
else
    echo "未找到运行中的 gateway 进程"
    echo ""
    echo "提示：如果服务确实在运行，可以尝试以下命令："
    echo "  pkill -f 'run.py gateway'"
    echo "  killall -9 python"
fi

nohup python -u run.py gateway >> gateway.log 2>&1 &