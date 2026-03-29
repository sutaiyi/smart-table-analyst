import time

import streamlit as st
import streamlit.components.v1 as components

from config import DEFAULT_BASE_URL, DEFAULT_API_KEY, DEFAULT_MODEL
from core.llm_client import LLMClient
from core.data_loader import load_table, get_data_summary, build_preview_html, df_to_html
from core.prompt_builder import build_refine_messages, build_analyze_messages, build_revise_messages
from core.table_analyzer import extract_code, execute_analysis
from core.browser_store import (
    init_browser_store, is_loaded, get_config, save_config,
    get_history, save_history, delete_history, clear_history, update_history,
)
from export.excel_exporter import export_excel
from export.html_exporter import export_html
from export.pdf_exporter import export_pdf

st.set_page_config(
    page_title="智能表格分析",
    page_icon="📊",
    layout="wide",
)

# 隐藏 Streamlit 骨架屏 & 零高度组件占位
st.markdown("""
<style>
    [data-testid="stSkeleton"] { display: none !important; }
    .stDeployButton { display: none; }
    /* 隐藏 streamlit_js_eval / components.html(height=0) 产生的空容器 */
    [class*="st-key-_load_config"],
    [class*="st-key-_load_history"] {
        position: fixed !important;
        top: -9999px !important;
        height: 0 !important;
        overflow: hidden !important;
    }
    /* 隐藏 height=0 的 iframe 容器 */
    iframe[height="0"] {
        display: none !important;
    }
    .element-container:has(iframe[height="0"]) {
        position: fixed !important;
        top: -9999px !important;
        height: 0 !important;
        overflow: hidden !important;
    }
</style>
""", unsafe_allow_html=True)

# 注入 DocQA Chat Widget 到主页面 body 末尾
components.html("""
<script>
(function() {
    var parent = window.parent.document;
    if (!parent.getElementById('docqa-widget-script')) {
        var s = parent.createElement('script');
        s.id = 'docqa-widget-script';
        s.src = 'https://widget.docqa.xyz/widget/chat-widget.js';
        s.setAttribute('data-base-url', 'https://excelai.eyantang.cc');
        s.setAttribute('data-theme', 'dark');
        parent.body.appendChild(s);
    }
})();
</script>
""", height=0)


def _build_styled_table_html(table_html: str, title: str = "") -> str:
    """构建带工具栏（搜索、下载CSV、全屏）的合并单元格表格 HTML"""
    safe_title = title.replace('"', '&quot;').replace("'", "\\'")
    return f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    color: #1e293b; background: #fff; padding: 0;
}}
.toolbar {{
    display:flex; align-items:center; gap:8px; padding:6px 8px;
    background:#f8fafc; border:1px solid #e2e8f0; border-bottom:none; border-radius:8px 8px 0 0;
}}
.toolbar input[type="text"] {{
    flex:1; max-width:260px; padding:5px 10px; border:1px solid #cbd5e1;
    border-radius:6px; font-size:12px; outline:none;
}}
.toolbar input[type="text"]:focus {{ border-color:#2563eb; box-shadow:0 0 0 2px rgba(37,99,235,0.1); }}
.toolbar .btn {{
    padding:4px 10px; border:1px solid #cbd5e1; border-radius:6px;
    background:#fff; color:#475569; font-size:12px; cursor:pointer; white-space:nowrap;
}}
.toolbar .btn:hover {{ background:#f1f5f9; border-color:#94a3b8; color:#1e293b; }}
.toolbar .match-info {{ font-size:11px; color:#94a3b8; white-space:nowrap; }}
.table-wrap {{ overflow:auto; max-height:500px; border:1px solid #e2e8f0; border-radius:0 0 8px 8px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; line-height:1.5; }}
thead th {{
    background:#f3f4f6; color:#1e293b;
    padding:11px 14px; text-align:left; font-weight:600; font-size:13px;
    border:1px solid #d1d5db; white-space:nowrap; position:sticky; top:0; z-index:2;
}}

/* 通用 td 样式 */
tbody td {{
    padding: 9px 14px;
    border: 1px solid #d1d5db;
    vertical-align: middle;
    color: #334155;
    background: #fff;
}}

/* 合并单元格：与普通单元格一致 */
tbody td.merged, tbody td[rowspan]:not(.merged) {{
    vertical-align: middle;
}}

/* 数字列 */
tbody td.num, thead th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}

/* 小计/合计行 */
tbody tr.subtotal td {{ font-weight:600; border-top:2px solid #94a3b8; }}
tbody tr.total td {{ font-weight:700; border-top:2px solid #64748b; font-size:13.5px; }}

/* 搜索高亮 */
mark {{ background:#fef08a; padding:1px 2px; border-radius:2px; }}

/* 全屏模式 */
body.fullscreen {{
    background: #fff; padding: 12px; margin: 0;
    display: flex; flex-direction: column; height: 100vh;
}}
body.fullscreen .toolbar {{ flex-shrink: 0; }}
body.fullscreen .table-wrap {{ flex: 1; max-height: none !important; border-radius: 0 0 8px 8px; }}
</style></head>
<body>
<div class="toolbar">
    <input type="text" id="searchBox" placeholder="搜索表格内容..." oninput="doSearch()">
    <span class="match-info" id="matchInfo"></span>
    <button class="btn" onclick="downloadExcel()">📥 下载Excel</button>
    <button class="btn" onclick="downloadCSV()">📥 下载CSV</button>
    <button class="btn" onclick="toggleFullscreen()" id="fsBtn">🔍 放大</button>
</div>
<div class="table-wrap" id="tableWrap">{table_html}</div>
<script>
// 搜索
function doSearch() {{
    const q = document.getElementById('searchBox').value.trim().toLowerCase();
    const cells = document.querySelectorAll('#tableWrap td, #tableWrap th');
    cells.forEach(c => {{ if(c._orig!==undefined) c.innerHTML=c._orig; }});
    if(!q) {{ document.getElementById('matchInfo').textContent=''; return; }}
    let n=0;
    cells.forEach(c => {{
        c._orig = c._orig===undefined ? c.innerHTML : c._orig;
        if(c.textContent.toLowerCase().includes(q)) {{
            const re = new RegExp('('+q.replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&')+')','gi');
            c.innerHTML = c._orig.replace(re,'<mark>$1</mark>'); n++;
        }}
    }});
    document.getElementById('matchInfo').textContent = n>0 ? n+' 个匹配' : '无匹配';
}}

// 解析表格为网格 + 合并信息
function parseTable() {{
    const table = document.querySelector('table');
    const trs = table.querySelectorAll('tr');
    const numRows = trs.length;
    let maxCols = 0;
    trs.forEach(tr => {{
        let c = 0;
        tr.querySelectorAll('th,td').forEach(cell => {{ c += (parseInt(cell.getAttribute('colspan'))||1); }});
        if(c > maxCols) maxCols = c;
    }});
    const grid = Array.from({{length:numRows}}, () => new Array(maxCols).fill(null));
    const merges = [];
    trs.forEach((tr, ri) => {{
        let ci = 0;
        tr.querySelectorAll('th,td').forEach(cell => {{
            while(ci < maxCols && grid[ri][ci] !== null) ci++;
            if(ci >= maxCols) return;
            const rs = parseInt(cell.getAttribute('rowspan')) || 1;
            const cs = parseInt(cell.getAttribute('colspan')) || 1;
            const txt = cell.textContent.trim();
            for(let dr=0; dr<rs && ri+dr<numRows; dr++) {{
                for(let dc=0; dc<cs && ci+dc<maxCols; dc++) {{
                    grid[ri+dr][ci+dc] = txt;
                }}
            }}
            if(rs > 1 || cs > 1) {{
                merges.push({{s:{{r:ri,c:ci}}, e:{{r:ri+rs-1,c:ci+cs-1}}}});
            }}
            ci += cs;
        }});
    }});
    return {{grid, merges, numRows, maxCols}};
}}

// 通用下载函数：兼容 iframe 沙箱
function triggerDownload(blob, filename) {{
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    // 在 parent 或当前窗口触发下载
    try {{
        (window.parent || window).document.body.appendChild(a);
        a.click();
        (window.parent || window).document.body.removeChild(a);
    }} catch(e) {{
        // 跨域限制时在当前 frame 下载
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }}
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}}

// 下载 Excel（带合并单元格，使用 SheetJS）
async function downloadExcel() {{
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '⏳ 加载中...';
    try {{
        if(!window.XLSX) {{
            const s = document.createElement('script');
            s.src = 'https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js';
            document.head.appendChild(s);
            await new Promise((resolve, reject) => {{
                s.onload = resolve;
                s.onerror = () => reject(new Error('SheetJS CDN 不可达'));
                setTimeout(() => reject(new Error('加载超时')), 8000);
            }});
        }}
        const {{grid, merges, numRows, maxCols}} = parseTable();
        const ws = XLSX.utils.aoa_to_sheet(grid);
        ws['!merges'] = merges;
        ws['!cols'] = Array.from({{length:maxCols}}, () => ({{wch:18}}));
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, '数据');
        XLSX.writeFile(wb, '{safe_title}.xlsx');
    }} catch(e) {{
        // CDN 加载失败时降级为 CSV 下载
        alert('Excel 生成失败（' + e.message + '），将自动下载 CSV 格式。');
        downloadCSV();
    }} finally {{
        btn.disabled = false;
        btn.textContent = '📥 下载Excel';
    }}
}}

// 下载 CSV（合并区域所有行填充相同值）
function downloadCSV() {{
    const {{grid}} = parseTable();
    const csv = grid.map(row => row.map(v => '"'+(v===null?'':v).replace(/"/g,'""')+'"').join(',')).join('\\n');
    const blob = new Blob(['\\uFEFF'+csv], {{type:'text/csv;charset=utf-8;'}});
    triggerDownload(blob, '{safe_title}.csv');
}}

// 全屏（使用浏览器 Fullscreen API）
function toggleFullscreen() {{
    const el = document.documentElement;
    if (!document.fullscreenElement) {{
        (el.requestFullscreen || el.webkitRequestFullscreen || el.msRequestFullscreen).call(el);
    }} else {{
        (document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen).call(document);
    }}
}}
document.addEventListener('fullscreenchange', () => {{
    const isFS = !!document.fullscreenElement;
    document.body.classList.toggle('fullscreen', isFS);
    document.getElementById('fsBtn').textContent = isFS ? '↩ 还原' : '🔍 放大';
    // 全屏时取消表格高度限制
    document.getElementById('tableWrap').style.maxHeight = isFS ? 'none' : '500px';
}});
</script>
</body></html>"""

# ── 从浏览器 localStorage 加载配置和历史 ──
init_browser_store()

# ── 侧边栏：模型配置 ──
_saved_config = get_config()
with st.sidebar:
    st.header("模型配置")
    base_url = st.text_input("API 接口地址",
                              value=_saved_config.get("base_url", DEFAULT_BASE_URL))
    api_key = st.text_input("API 密钥",
                             value=_saved_config.get("api_key", DEFAULT_API_KEY),
                             type="password")
    model_name = st.text_input("模型名称",
                                value=_saved_config.get("model", DEFAULT_MODEL))

    if st.button("💾 保存配置"):
        save_config(base_url, api_key, model_name)
        st.success("配置已保存到浏览器")

    st.divider()
    st.caption("支持所有兼容 OpenAI 格式的 API")
    st.caption("如 OpenAI、DeepSeek、Kimi、通义千问、Ollama 等")

    # ── 历史记录 ──
    st.divider()
    st.header("历史记录")
    history_records = get_history()

    if history_records:
        if st.button("🗑️ 清空全部历史", key="clear_all"):
            clear_history()
            st.rerun()

        for rec in history_records:
            file_name = rec.get("file_name", "未知文件")
            request_preview = rec.get("user_request", "")[:40]
            created_at = rec.get("created_at", "")
            rec_id = rec.get("id")

            with st.container():
                revisions = rec.get("revisions", [])
                rev_tag = f" · 修正{len(revisions)}次" if revisions else ""
                st.caption(f"📄 {file_name} · {created_at}{rev_tag}")
                st.text(request_preview + ("..." if len(rec.get("user_request", "")) > 40 else ""))
                col_use, col_del = st.columns([1, 1])
                with col_use:
                    if st.button("复用", key=f"use_{rec_id}"):
                        st.session_state.prefill_request = rec.get("user_request", "")
                        if rec.get("refined_prompt"):
                            st.session_state.refined_prompt = rec.get("refined_prompt")
                        st.rerun()
                with col_del:
                    if st.button("删除", key=f"del_{rec_id}"):
                        delete_history(rec_id)
                        st.rerun()
                st.divider()
    else:
        st.caption("暂无历史记录")

# ── 主界面 ──
st.title("📊 智能表格分析")
st.markdown("上传表格 → 描述需求 → AI分析 → 导出报告")

# 初始化 session state
for key in ["df", "data_summary", "refined_prompt", "analysis_result", "file_name", "prefill_request",
            "last_code", "revision_history", "current_history_id", "merges"]:
    if key not in st.session_state:
        st.session_state[key] = None
if st.session_state.revision_history is None:
    st.session_state.revision_history = []

# ── 步骤1: 上传文件 ──
st.subheader("① 上传表格文件")
uploaded_file = st.file_uploader(
    "支持 Excel (.xlsx/.xls) 和 CSV 格式",
    type=["xlsx", "xls", "csv"],
)

if uploaded_file:
    try:
        df, merges = load_table(uploaded_file)
        st.session_state.df = df
        st.session_state.merges = merges
        st.session_state.data_summary = get_data_summary(df)
        st.session_state.file_name = uploaded_file.name

        st.success(f"已加载 {len(df)} 行 × {len(df.columns)} 列")
        with st.expander("预览数据（全部）", expanded=True):
            if merges:
                # 有合并单元格，用 HTML 渲染保留合并效果
                preview_html = build_preview_html(df, merges)
                full_html = _build_styled_table_html(preview_html, st.session_state.file_name or "数据预览")
                components.html(full_html, height=560, scrolling=False)
            else:
                st.dataframe(df, height=400, use_container_width=True)
    except Exception as e:
        st.error(f"加载文件失败: {e}")

# ── 步骤2: 描述分析需求 ──
if st.session_state.df is not None:
    st.subheader("② 描述你的分析需求")
    # 如果从历史记录复用，先写入 widget 的 key 对应的 session_state
    if st.session_state.prefill_request:
        st.session_state["user_request_input"] = st.session_state.prefill_request
        st.session_state.prefill_request = None
    user_request = st.text_area(
        "请描述你想要的分析（越详细越好）",
        placeholder="例如：按部门统计销售额，分析各月趋势，找出TOP10客户，对比同比环比增长率...",
        height=100,
        key="user_request_input",
    )

    # ── 步骤3: 生成分析方案 / 直接分析 ──
    st.markdown(
        '<div style="display:flex;gap:20px;">',
        unsafe_allow_html=True,
    )
    col_btn1, col_btn2, col_spacer = st.columns([2, 2, 8])
    with col_btn1:
        btn_refine = st.button("🔍 生成分析方案", type="primary", disabled=not user_request, use_container_width=True)
    with col_btn2:
        btn_direct = st.button("⚡ 直接出结果", disabled=not user_request, use_container_width=True)

    def _save_history_record(user_req, refined=""):
        from datetime import datetime
        history_id = int(time.time() * 1000)
        record = {
            "id": history_id,
            "file_name": st.session_state.file_name or "未知文件",
            "user_request": user_req,
            "refined_prompt": refined,
            "revisions": [],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        save_history(record)
        st.session_state.current_history_id = history_id

    if btn_refine:
        if not api_key:
            st.error("请先在侧边栏配置 API Key")
        else:
            with st.spinner("AI正在理解你的需求..."):
                try:
                    client = LLMClient(base_url, api_key, model_name)
                    messages = build_refine_messages(user_request, st.session_state.data_summary)
                    refined = client.chat(messages, temperature=0.7)
                    st.session_state.refined_prompt = refined
                    st.session_state.analysis_result = None
                    _save_history_record(user_request, refined)
                except Exception as e:
                    st.error(f"AI调用失败: {e}")

    if btn_direct:
        if not api_key:
            st.error("请先在侧边栏配置 API Key")
        else:
            progress = st.empty()
            try:
                # 直接把用户输入当作分析需求生成代码（适合粘贴已有的分析方案）
                progress.info("⏳ AI正在生成分析代码...")
                client = LLMClient(base_url, api_key, model_name)
                messages = build_analyze_messages(user_request, st.session_state.data_summary)
                response = client.chat(messages, temperature=0.2)
                code = extract_code(response)

                progress.info("⏳ 正在执行分析...")
                result = execute_analysis(code, st.session_state.df, llm_client=client)
                st.session_state.analysis_result = result
                st.session_state.last_code = code
                st.session_state.revision_history = []
                st.session_state.refined_prompt = None
                _save_history_record(user_request)
                progress.success("分析完成！")
            except Exception as e:
                progress.empty()
                st.error(f"分析执行失败: {e}")

    # ── 步骤4: 确认/编辑提示词 ──
    if st.session_state.refined_prompt:
        st.subheader("③ 确认分析方案")
        st.info("你可以编辑下方的分析方案，然后点击确认执行")

        edited_prompt = st.text_area(
            "分析方案（可编辑）",
            value=st.session_state.refined_prompt,
            height=300,
        )

        # ── 步骤5: 执行分析 ──
        if st.button("✅ 确认并执行分析", type="primary"):
            with st.spinner("AI正在分析数据，请稍候..."):
                try:
                    client = LLMClient(base_url, api_key, model_name)
                    messages = build_analyze_messages(edited_prompt, st.session_state.data_summary)
                    response = client.chat(messages, temperature=0.2)
                    code = extract_code(response)

                    with st.expander("查看生成的分析代码"):
                        st.code(code, language="python")

                    result = execute_analysis(code, st.session_state.df, llm_client=client)
                    st.session_state.analysis_result = result
                    st.session_state.last_code = code
                    st.session_state.revision_history = []
                    st.success("分析完成！")
                except Exception as e:
                    st.error(f"分析执行失败: {e}")

    # ── 渲染结果的公共函数 ──
    def _render_result(result: dict, key_suffix: str = ""):
        """渲染分析结果（摘要 + 图表 + 表格）"""
        import plotly.express as px

        if result.get("summary"):
            st.markdown("**分析摘要**")
            st.markdown(result["summary"])

        if result.get("charts"):
            for idx, chart_config in enumerate(result["charts"]):
                chart_type = chart_config.get("type", "bar")
                data = chart_config.get("data")
                title = chart_config.get("title", "")
                x = chart_config.get("x")
                y = chart_config.get("y")

                if data is None:
                    continue

                fig = None
                if chart_type == "bar":
                    fig = px.bar(data, x=x, y=y, title=title)
                elif chart_type == "line":
                    fig = px.line(data, x=x, y=y, title=title)
                elif chart_type == "pie":
                    fig = px.pie(
                        data,
                        names=chart_config.get("labels"),
                        values=chart_config.get("values"),
                        title=title,
                    )
                elif chart_type == "scatter":
                    fig = px.scatter(data, x=x, y=y, title=title)
                elif chart_type == "heatmap":
                    fig = px.imshow(data, title=title, text_auto=True, aspect="auto")

                if fig:
                    fig.update_layout(template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True,
                                    key=f"chart_{key_suffix}_{idx}")

        if result.get("result_tables"):
            for tbl_title, tbl_df in result["result_tables"].items():
                st.markdown(f"**{tbl_title}**")
                # 自动检测分组列并合并连续相同值，生成带 rowspan 的 HTML
                table_html = df_to_html(tbl_df, auto_merge=True)
                full_html = _build_styled_table_html(table_html, tbl_title)
                row_count = table_html.count("<tr")
                iframe_height = min(row_count * 40 + 80, 560)
                iframe_height = max(iframe_height, 200)
                components.html(full_html, height=iframe_height, scrolling=False)

    def _render_export(result: dict, key_suffix: str = ""):
        """渲染导出按钮"""
        col1, col2, col3 = st.columns(3)
        report_title = st.text_input("报告标题", value="数据分析报告",
                                      key=f"report_title_{key_suffix}")

        # 为导出生成带合并的 HTML 表格
        auto_styled = {}
        for tbl_title, tbl_df in result.get("result_tables", {}).items():
            auto_styled[tbl_title] = df_to_html(tbl_df, auto_merge=True)

        with col1:
            try:
                excel_bytes = export_excel(
                    result["result_tables"], result.get("summary", ""),
                    styled_tables=auto_styled,
                )
                st.download_button(
                    "📥 下载 Excel", data=excel_bytes,
                    file_name=f"{report_title}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_excel_{key_suffix}",
                )
            except Exception as e:
                st.error(f"Excel导出失败: {e}")

        with col2:
            try:
                html_content = export_html(
                    result["result_tables"], result.get("charts", []),
                    result.get("summary", ""), title=report_title,
                    styled_tables=auto_styled,
                )
                st.download_button(
                    "📥 下载 HTML", data=html_content,
                    file_name=f"{report_title}.html", mime="text/html",
                    key=f"dl_html_{key_suffix}",
                )
            except Exception as e:
                st.error(f"HTML导出失败: {e}")

        with col3:
            try:
                pdf_bytes = export_pdf(
                    result["result_tables"], result.get("charts", []),
                    result.get("summary", ""), title=report_title,
                    styled_tables=auto_styled,
                )
                st.download_button(
                    "📥 下载 PDF", data=pdf_bytes,
                    file_name=f"{report_title}.pdf", mime="application/pdf",
                    key=f"dl_pdf_{key_suffix}",
                )
            except Exception as e:
                st.warning(f"PDF导出需要安装 WeasyPrint 系统依赖，详见 README。错误: {e}")

    # ── 展示初始分析结果 ──
    if st.session_state.analysis_result:
        st.subheader("④ 分析结果（初始）")
        _render_result(st.session_state.analysis_result, key_suffix="init")

        # 如果没有修正，导出按钮放在初始结果下方
        if not st.session_state.revision_history:
            st.subheader("⑤ 导出报告")
            _render_export(st.session_state.analysis_result, key_suffix="init")

        # ── 展示每次修正的结果 ──
        for i, rev in enumerate(st.session_state.revision_history):
            st.divider()
            st.subheader(f"修正 {i + 1}")
            st.markdown(f"**修改意见：** {rev['feedback']}")
            if rev.get("result"):
                _render_result(rev["result"], key_suffix=f"rev_{i}")

        # 最后一次修正的结果提供导出
        if st.session_state.revision_history:
            latest_rev = st.session_state.revision_history[-1]
            if latest_rev.get("result"):
                st.divider()
                st.subheader("⑤ 导出报告（最新版本）")
                _render_export(latest_rev["result"], key_suffix="latest")

        # ── 多轮修正输入 ──
        st.divider()
        st.subheader("⑥ 继续修正")
        st.info("对分析结果不满意？描述你的修改意见，AI 会在当前结果基础上调整。")

        with st.form(key="revision_form", clear_on_submit=False):
            revision_input = st.text_area(
                "修改意见",
                placeholder="例如：把柱状图改成折线图、去掉第三列、增加环比增长率计算、表格按降序排列...",
                height=80,
            )
            submitted = st.form_submit_button("🔄 提交修改", type="primary")

        pending = revision_input.strip() if submitted and revision_input.strip() else None
        if pending:
            if not api_key:
                st.error("请先在侧边栏配置 API Key")
            elif not st.session_state.last_code:
                st.error("没有可修正的分析代码")
            else:
                with st.spinner("AI正在修正分析结果..."):
                    try:
                        client = LLMClient(base_url, api_key, model_name)

                        conv_history = []
                        for rev in st.session_state.revision_history:
                            conv_history.append({"role": "user", "content": rev["feedback"]})
                            conv_history.append({
                                "role": "assistant",
                                "content": f"```python\n{rev['code']}\n```",
                            })

                        messages = build_revise_messages(
                            user_feedback=pending,
                            previous_code=st.session_state.last_code,
                            data_summary=st.session_state.data_summary,
                            conversation_history=conv_history,
                        )
                        response = client.chat(messages, temperature=0.2)
                        new_code = extract_code(response)

                        new_result = execute_analysis(
                            new_code, st.session_state.df, llm_client=client
                        )

                        # 更新状态：结果存入修正历史，不覆盖原始结果
                        st.session_state.revision_history.append({
                            "feedback": pending,
                            "code": new_code,
                            "result": new_result,
                        })
                        st.session_state.last_code = new_code

                        # 将修改意见追加到历史记录
                        if st.session_state.current_history_id:
                            from datetime import datetime
                            revision_entry = {
                                "feedback": pending,
                                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            }
                            history = get_history()
                            for rec in history:
                                if rec.get("id") == st.session_state.current_history_id:
                                    revisions = rec.get("revisions", [])
                                    revisions.append(revision_entry)
                                    update_history(st.session_state.current_history_id, {
                                        "revisions": revisions,
                                    })
                                    break

                        st.rerun()
                    except Exception as e:
                        st.error(f"修正失败: {e}")
