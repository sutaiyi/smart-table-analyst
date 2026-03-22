#!/bin/bash
#
# Smart Table Analyst 部署脚本
# 适用于 Alibaba Cloud Linux 3 (基于 RHEL 8/CentOS 8)
#
# 用法:
#   chmod +x deploy.sh
#   ./deploy.sh              # 首次部署
#   ./deploy.sh update       # 更新代码并重启
#   ./deploy.sh restart      # 仅重启服务
#   ./deploy.sh stop         # 停止服务
#   ./deploy.sh status       # 查看服务状态
#   ./deploy.sh logs         # 查看日志

set -e

# ============ 配置项（根据需要修改）============
APP_NAME="smart-table-analyst"
APP_DIR="/opt/${APP_NAME}"
REPO_URL="https://github.com/sutaiyi/smart-table-analyst.git"
PYTHON_VERSION="3.10"
PORT=8501
USER="app"                    # 运行服务的用户
VENV_DIR="${APP_DIR}/.venv"
SERVICE_NAME="${APP_NAME}"
# ================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请用 root 用户运行: sudo ./deploy.sh"
        exit 1
    fi
}

# ──────────────────────────────────────────────
# 安装系统依赖
# ──────────────────────────────────────────────
install_system_deps() {
    log_info "安装系统依赖..."

    # 基础工具
    yum install -y git gcc make wget curl

    # ── 安装 Python 3.10 ──
    if command -v python3.10 &>/dev/null; then
        PYTHON_BIN="python3.10"
        log_info "Python 3.10 已存在，跳过安装"
    else
        log_info "安装 Python 3.10（源码编译，约5-10分钟）..."
        yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel \
            readline-devel sqlite-devel xz-devel tk-devel gdbm-devel

        PYTHON_FULL="3.10.16"
        cd /tmp
        rm -rf Python-${PYTHON_FULL}*

        log_info "下载 Python ${PYTHON_FULL}..."
        wget "https://www.python.org/ftp/python/${PYTHON_FULL}/Python-${PYTHON_FULL}.tgz"
        if [ ! -f "Python-${PYTHON_FULL}.tgz" ]; then
            log_error "Python 源码下载失败，请检查网络"
            exit 1
        fi

        tar xzf "Python-${PYTHON_FULL}.tgz"
        cd "Python-${PYTHON_FULL}"

        log_info "编译中（configure）..."
        ./configure --enable-optimizations --prefix=/usr/local
        log_info "编译中（make），请耐心等待..."
        make -j$(nproc)
        log_info "安装中（make altinstall）..."
        make altinstall

        cd /
        rm -rf /tmp/Python-${PYTHON_FULL}*

        # 验证安装
        if command -v python3.10 &>/dev/null; then
            log_info "Python 3.10 安装成功: $(python3.10 --version)"
        elif [ -f /usr/local/bin/python3.10 ]; then
            ln -sf /usr/local/bin/python3.10 /usr/bin/python3.10
            ln -sf /usr/local/bin/pip3.10 /usr/bin/pip3.10
            log_info "Python 3.10 安装成功: $(python3.10 --version)"
        else
            log_error "Python 3.10 编译安装失败"
            exit 1
        fi
        PYTHON_BIN="python3.10"
    fi

    log_info "使用 Python: $(${PYTHON_BIN} --version)"

    # WeasyPrint 系统依赖（PDF 导出）
    log_info "安装 WeasyPrint 依赖（PDF导出）..."
    yum install -y pango pango-devel cairo cairo-devel gobject-introspection-devel \
        gdk-pixbuf2 gdk-pixbuf2-devel libffi-devel || true

    # 中文字体（报告中文显示）
    log_info "安装中文字体..."
    yum install -y google-noto-sans-cjk-fonts wqy-microhei-fonts || \
    yum install -y google-noto-sans-sc-fonts || true
}

# ──────────────────────────────────────────────
# 创建应用用户
# ──────────────────────────────────────────────
create_user() {
    if ! id "${USER}" &>/dev/null; then
        log_info "创建应用用户: ${USER}"
        useradd -r -m -s /bin/bash "${USER}"
    fi
}

# ──────────────────────────────────────────────
# 拉取/更新代码
# ──────────────────────────────────────────────
setup_code() {
    if [ -d "${APP_DIR}/.git" ]; then
        log_info "更新代码..."
        cd "${APP_DIR}"
        git pull origin master || git pull origin main
    else
        log_info "克隆代码..."
        git clone "${REPO_URL}" "${APP_DIR}"
    fi
    chown -R "${USER}:${USER}" "${APP_DIR}"
}

# ──────────────────────────────────────────────
# 创建虚拟环境 & 安装依赖
# ──────────────────────────────────────────────
setup_venv() {
    log_info "创建虚拟环境..."
    cd "${APP_DIR}"

    if [ ! -d "${VENV_DIR}" ]; then
        sudo -u "${USER}" ${PYTHON_BIN} -m venv "${VENV_DIR}"
    fi

    log_info "安装 Python 依赖..."
    sudo -u "${USER}" "${VENV_DIR}/bin/pip" install --upgrade pip -q
    sudo -u "${USER}" "${VENV_DIR}/bin/pip" install -r requirements.txt -q
    log_info "依赖安装完成"
}

# ──────────────────────────────────────────────
# 创建 .env 配置文件（如果不存在）
# ──────────────────────────────────────────────
setup_env() {
    if [ ! -f "${APP_DIR}/.env" ]; then
        log_warn ".env 文件不存在，从模板创建..."
        sudo -u "${USER}" cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
        log_warn "请编辑 ${APP_DIR}/.env 填入你的 API 配置"
    fi
}

# ──────────────────────────────────────────────
# 创建 Streamlit 配置
# ──────────────────────────────────────────────
setup_streamlit_config() {
    local config_dir="${APP_DIR}/.streamlit"
    mkdir -p "${config_dir}"
    cat > "${config_dir}/config.toml" << 'EOF'
[server]
port = ${PORT}
address = "0.0.0.0"
headless = true
enableCORS = false
enableXsrfProtection = false
maxUploadSize = 200

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#2563eb"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f8fafc"
textColor = "#1e293b"
EOF
    # 替换端口变量
    sed -i "s/\${PORT}/${PORT}/g" "${config_dir}/config.toml"
    chown -R "${USER}:${USER}" "${config_dir}"
}

# ──────────────────────────────────────────────
# 创建数据目录
# ──────────────────────────────────────────────
setup_data_dir() {
    mkdir -p "${APP_DIR}/data"
    chown -R "${USER}:${USER}" "${APP_DIR}/data"
}

# ──────────────────────────────────────────────
# 创建 systemd 服务
# ──────────────────────────────────────────────
create_service() {
    log_info "创建 systemd 服务..."
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Smart Table Analyst - AI表格分析工具
After=network.target

[Service]
Type=simple
User=${USER}
Group=${USER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin"
ExecStart=${VENV_DIR}/bin/streamlit run app.py \\
    --server.port=${PORT} \\
    --server.address=0.0.0.0 \\
    --server.headless=true \\
    --server.maxUploadSize=200
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# 安全加固
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=${APP_DIR}/data
ProtectHome=true

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}"
    log_info "systemd 服务创建完成"
}

# ──────────────────────────────────────────────
# 配置防火墙
# ──────────────────────────────────────────────
setup_firewall() {
    if command -v firewall-cmd &>/dev/null; then
        log_info "配置防火墙放行端口 ${PORT}..."
        firewall-cmd --permanent --add-port=${PORT}/tcp 2>/dev/null || true
        firewall-cmd --reload 2>/dev/null || true
    fi
    # 阿里云安全组提示
    log_warn "如果外网访问不了，请在阿里云控制台的安全组中放行 TCP ${PORT} 端口"
}

# ──────────────────────────────────────────────
# 启动/重启服务
# ──────────────────────────────────────────────
start_service() {
    log_info "启动服务..."
    systemctl restart "${SERVICE_NAME}"
    sleep 3
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log_info "服务启动成功！"
        local ip=$(hostname -I | awk '{print $1}')
        echo ""
        echo "========================================"
        echo "  Smart Table Analyst 部署完成！"
        echo "========================================"
        echo "  内网访问: http://${ip}:${PORT}"
        echo "  本地访问: http://localhost:${PORT}"
        echo ""
        echo "  配置文件: ${APP_DIR}/.env"
        echo "  查看日志: journalctl -u ${SERVICE_NAME} -f"
        echo "  重启服务: systemctl restart ${SERVICE_NAME}"
        echo "  停止服务: systemctl stop ${SERVICE_NAME}"
        echo "========================================"
    else
        log_error "服务启动失败，查看日志:"
        journalctl -u "${SERVICE_NAME}" --no-pager -n 20
        exit 1
    fi
}

stop_service() {
    log_info "停止服务..."
    systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
    log_info "服务已停止"
}

show_status() {
    systemctl status "${SERVICE_NAME}" --no-pager
}

show_logs() {
    journalctl -u "${SERVICE_NAME}" -f --no-pager
}

# ──────────────────────────────────────────────
# 首次完整部署
# ──────────────────────────────────────────────
full_deploy() {
    check_root
    log_info "开始完整部署 Smart Table Analyst..."
    install_system_deps
    create_user
    setup_code
    setup_venv
    setup_env
    setup_streamlit_config
    setup_data_dir
    create_service
    setup_firewall
    start_service
}

# ──────────────────────────────────────────────
# 更新部署
# ──────────────────────────────────────────────
update_deploy() {
    check_root
    log_info "更新部署..."
    setup_code
    setup_venv
    start_service
}

# ──────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────
case "${1:-}" in
    update)
        update_deploy
        ;;
    restart)
        check_root
        start_service
        ;;
    stop)
        check_root
        stop_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    *)
        full_deploy
        ;;
esac
