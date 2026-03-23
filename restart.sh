#!/bin/bash
# 更新依赖并重启 Smart Table Analyst
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${APP_DIR}"


source .venv/bin/activate
pip install -r requirements.txt

echo "拉拉取最新代码"
git pull

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
