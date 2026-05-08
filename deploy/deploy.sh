#!/bin/bash
# 日常更新部署脚本（每次推送新代码后在服务器上执行）
# 用法：bash deploy/deploy.sh
set -e

REPO_DIR="/root/pa-agent"
cd "$REPO_DIR"

echo "=== 拉取最新代码 ==="
git pull

echo "=== 更新依赖 ==="
.venv/bin/pip install -r requirements-server.txt -q

echo "=== 重启服务 ==="
systemctl restart pa-agent
sleep 2
systemctl status pa-agent --no-pager

echo "=== 部署完成 ==="
