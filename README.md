# Smart Table Analyst 📊

基于 AI 的智能表格分析工具。上传表格、描述需求，AI 自动生成分析报告（Excel / HTML / PDF），含图表，领导一看就懂。

## 功能特点

- **需求理解**: 用自然语言描述分析需求，AI 自动转化为结构化分析方案
- **方案可控**: 生成的分析方案可编辑确认，确保分析方向正确
- **自动分析**: AI 编写并执行分析代码，生成表格和图表
- **多格式导出**: 支持 Excel（带格式）、HTML（交互图表）、PDF 报告
- **模型可配**: 支持 OpenAI、DeepSeek、通义千问、Ollama 等任何兼容 OpenAI 格式的 API

## 快速开始

### 1. 创建虚拟环境

```bash
cd /path/to/smart-table-analyst
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

> **macOS SSL 证书问题**：如果安装时报 `SSL: CERTIFICATE_VERIFY_FAILED`，先运行：
> ```bash
> # 方法A：安装 Python 证书（推荐，路径根据你的 Python 版本调整）
> /Applications/Python\ 3.10/Install\ Certificates.command
>
> # 方法B：临时跳过 SSL 验证
> pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt
> ```

> **PDF 导出**需要额外安装 WeasyPrint 系统依赖：
> - macOS: `brew install pango`
> - Ubuntu: `apt-get install libpango-1.0-0 libpangocairo-1.0-0`

### 3. 配置

复制环境变量文件并填入你的 API 配置：

```bash
cp .env.example .env
```

编辑 `.env`：
```
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=gpt-4o
```

也可以在 Web 界面侧边栏直接配置，无需 `.env` 文件。

### 4. 启动

```bash
source .venv/bin/activate  # 如果尚未激活虚拟环境
streamlit run app.py
```

浏览器访问 `http://localhost:8501`

## 使用流程

1. **上传表格** — 支持 .xlsx / .xls / .csv
2. **描述需求** — 用中文描述你想分析什么
3. **确认方案** — AI 生成分析方案，可编辑调整
4. **查看结果** — 表格 + 图表展示分析结果
5. **导出报告** — 下载 Excel / HTML / PDF

## 支持的模型

通过 `base_url` 适配不同 AI 服务：

| 服务 | Base URL |
|------|----------|
| OpenAI | `https://api.openai.com/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| Ollama (本地) | `http://localhost:11434/v1` |

## 技术栈

- **前端**: Streamlit
- **图表**: Plotly
- **AI**: OpenAI 兼容接口
- **PDF**: WeasyPrint
- **数据**: pandas + openpyxl
