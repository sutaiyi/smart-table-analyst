#!/bin/bash
# 更新依赖并重启 Smart Table Analyst
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${APP_DIR}"
echo "拉拉取最新代码"
git pull
echo "📦 更新依赖..."
source .venv/bin/activate
pip install -r requirements.txt

# Playwright 浏览器（PDF导出用，已安装则跳过）
if grep -q "playwright" requirements.txt; then
    if python -c "from playwright.sync_api import sync_playwright; sync_playwright().start().chromium.executable_path" 2>/dev/null; then
        echo "✅ Playwright Chromium 已安装，跳过"
    else
        echo "🌐 安装 Playwright Chromium..."
        playwright install chromium
        playwright install-deps chromium 2>/dev/null || true
    fi
fi

echo "🔄 重启服务..."
pkill -f "streamlit run app.py" 2>/dev/null || true
sleep 1

nohup .venv/bin/streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.maxUploadSize=200 \
    > app.log 2>&1 &

sleep 3
if curl -s http://localhost:8501 > /dev/null; then
    echo "✅ 启动成功！"
else
    echo "❌ 启动可能失败，查看日志："
    tail -20 app.log
fi
