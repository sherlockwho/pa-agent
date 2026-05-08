#!/bin/bash
# 服务器一次性初始化脚本
# 用法：bash deploy/setup.sh
set -e

REPO_DIR="/root/pa-agent"
GITHUB_REPO="https://github.com/YOUR_USERNAME/YOUR_REPO.git"  # ← 改成你的仓库地址

echo "=== [1/7] 添加 swap (2GB) ==="
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "vm.swappiness=10" >> /etc/sysctl.conf
    sysctl -p
    echo "Swap 已创建"
else
    echo "Swap 已存在，跳过"
fi

echo "=== [2/7] 安装系统依赖 ==="
apt-get update -q
apt-get install -y -q python3.11 python3.11-venv python3-pip git nginx certbot python3-certbot-nginx

echo "=== [3/7] 克隆代码 ==="
if [ -d "$REPO_DIR" ]; then
    echo "目录已存在，执行 git pull"
    cd "$REPO_DIR" && git pull
else
    git clone "$GITHUB_REPO" "$REPO_DIR"
    cd "$REPO_DIR"
fi

echo "=== [4/7] 创建虚拟环境并安装依赖 ==="
cd "$REPO_DIR"
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements-server.txt -q
echo "依赖安装完成"

echo "=== [5/7] 创建数据目录 ==="
mkdir -p data/{conversations,tasks,calendar,entities,documents,memory}
touch data/.gitkeep

echo "=== [6/7] 配置 Nginx ==="
cp deploy/nginx.conf /etc/nginx/sites-available/pa-agent
ln -sf /etc/nginx/sites-available/pa-agent /etc/nginx/sites-enabled/pa-agent
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "=== [7/7] 安装 systemd 服务 ==="
cp deploy/pa-agent.service /etc/systemd/system/pa-agent.service
systemctl daemon-reload
systemctl enable pa-agent

echo ""
echo "========================================"
echo "初始化完成！接下来手动执行："
echo ""
echo "1. 创建配置文件："
echo "   cp $REPO_DIR/config.example.yaml $REPO_DIR/config.yaml"
echo "   nano $REPO_DIR/config.yaml   # 填入 API Key 和 Token"
echo ""
echo "2. 申请 SSL 证书："
echo "   certbot --nginx -d api.cleverboy.fun --non-interactive --agree-tos -m your@email.com"
echo ""
echo "3. 启动服务："
echo "   systemctl start pa-agent"
echo "   systemctl status pa-agent"
echo "========================================"
