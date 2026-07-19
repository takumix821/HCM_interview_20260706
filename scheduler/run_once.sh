#!/bin/bash
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 開始執行 collect_articles.py"
python /app/collect_articles.py
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 執行結束"
