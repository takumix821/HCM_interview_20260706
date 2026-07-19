#!/bin/bash
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 容器啟動，執行初始化蒐集"
/app/scheduler/run_once.sh
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 初始化完成，交給 cron 排程"
exec cron -f
