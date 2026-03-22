import streamlit as st

from config import DEFAULT_BASE_URL, DEFAULT_API_KEY, DEFAULT_MODEL
from core.llm_client import LLMClient
from core.data_loader import load_table, get_data_summary
from core.prompt_builder import build_refine_messages, build_analyze_messages
from core.table_analyzer import extract_code, execute_analysis
from export.excel_exporter import export_excel
from export.html_exporter import export_html
from export.pdf_exporter import export_pdf

st.set_page_config(
    page_title="Smart Table Analyst",
    page_icon="📊",
    layout="wide",
)

# ── 侧边栏：模型配置 ──
with st.sidebar:
    st.header("模型配置")
    base_url = st.text_input("API Base URL", value=DEFAULT_BASE_URL)
    api_key = st.text_input("API Key", value=DEFAULT_API_KEY, type="password")
    model_name = st.text_input("模型名称", value=DEFAULT_MODEL)
    st.divider()
    st.caption("支持所有兼容 OpenAI 格式的 API")
    st.caption("如 OpenAI、DeepSeek、通义千问、Ollama 等")

# ── 主界面 ──
st.title("📊 Smart Table Analyst")
st.markdown("上传表格 → 描述需求 → AI分析 → 导出报告")

# 初始化 session state
for key in ["df", "data_summary", "refined_prompt", "analysis_result", "file_name"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ── 步骤1: 上传文件 ──
st.subheader("① 上传表格文件")
uploaded_file = st.file_uploader(
    "支持 Excel (.xlsx/.xls) 和 CSV 格式",
    type=["xlsx", "xls", "csv"],
)

if uploaded_file:
    try:
        df = load_table(uploaded_file)
        st.session_state.df = df
        st.session_state.data_summary = get_data_summary(df)
        st.session_state.file_name = uploaded_file.name

        st.success(f"已加载 {len(df)} 行 × {len(df.columns)} 列")
        with st.expander("预览数据（前10行）", expanded=True):
            st.dataframe(df.head(10), use_container_width=True)
    except Exception as e:
        st.error(f"加载文件失败: {e}")

# ── 步骤2: 描述分析需求 ──
if st.session_state.df is not None:
    st.subheader("② 描述你的分析需求")
    user_request = st.text_area(
        "请描述你想要的分析（越详细越好）",
        placeholder="例如：按部门统计销售额，分析各月趋势，找出TOP10客户，对比同比环比增长率...",
        height=100,
    )

    # ── 步骤3: 生成分析提示词 ──
    if st.button("🔍 生成分析方案", type="primary", disabled=not user_request):
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
                except Exception as e:
                    st.error(f"AI调用失败: {e}")

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

                    result = execute_analysis(code, st.session_state.df)
                    st.session_state.analysis_result = result
                    st.success("分析完成！")
                except Exception as e:
                    st.error(f"分析执行失败: {e}")

    # ── 步骤6: 展示结果与导出 ──
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result

        st.subheader("④ 分析结果")

        # 摘要
        if result.get("summary"):
            st.markdown("**分析摘要**")
            st.markdown(result["summary"])

        # 图表
        if result.get("charts"):
            import plotly.express as px
            import plotly.graph_objects as go

            for chart_config in result["charts"]:
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
                    st.plotly_chart(fig, use_container_width=True)

        # 表格
        if result.get("result_tables"):
            for tbl_title, tbl_df in result["result_tables"].items():
                st.markdown(f"**{tbl_title}**")
                st.dataframe(tbl_df, use_container_width=True)

        # ── 导出 ──
        st.subheader("⑤ 导出报告")
        col1, col2, col3 = st.columns(3)

        report_title = st.text_input("报告标题", value="数据分析报告")

        with col1:
            try:
                excel_bytes = export_excel(result["result_tables"], result.get("summary", ""))
                st.download_button(
                    "📥 下载 Excel",
                    data=excel_bytes,
                    file_name=f"{report_title}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            except Exception as e:
                st.error(f"Excel导出失败: {e}")

        with col2:
            try:
                html_content = export_html(
                    result["result_tables"],
                    result.get("charts", []),
                    result.get("summary", ""),
                    title=report_title,
                )
                st.download_button(
                    "📥 下载 HTML",
                    data=html_content,
                    file_name=f"{report_title}.html",
                    mime="text/html",
                )
            except Exception as e:
                st.error(f"HTML导出失败: {e}")

        with col3:
            try:
                pdf_bytes = export_pdf(
                    result["result_tables"],
                    result.get("charts", []),
                    result.get("summary", ""),
                    title=report_title,
                )
                st.download_button(
                    "📥 下载 PDF",
                    data=pdf_bytes,
                    file_name=f"{report_title}.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.warning(f"PDF导出需要安装 WeasyPrint 系统依赖，详见 README。错误: {e}")
