import pandas as pd
from playwright.sync_api import sync_playwright

from .html_exporter import export_html

# PDF 专用样式：注入到 HTML 中，覆盖屏幕样式以适配打印
_PDF_STYLE = """
<style>
body { background: white; font-size: 10px; }
.report-container { max-width: 100%; padding: 0; }
.report-header { padding: 20px; margin-bottom: 15px; border-radius: 6px; }
.report-header h1 { font-size: 20px; }
.summary-card, .chart-section, .table-section {
    padding: 15px; margin-bottom: 12px; border-radius: 6px;
    box-shadow: none; page-break-inside: avoid;
}
table { font-size: 9px; table-layout: auto; width: 100%; }
thead th { padding: 5px 4px; font-size: 9px; }
tbody td { padding: 4px 4px; font-size: 9px; }
</style>
"""


def export_pdf(
    result_tables: dict[str, pd.DataFrame],
    charts: list[dict],
    summary: str = "",
    title: str = "数据分析报告",
    styled_tables: dict[str, str] | None = None,
) -> bytes:
    html_content = export_html(
        result_tables=result_tables,
        charts=charts,
        summary=summary,
        title=title,
        styled_tables=styled_tables,
    )
    # 移除 plotly js 引用（PDF 不支持 JS）
    html_content = html_content.replace(
        '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>', ""
    )
    # 注入 PDF 专用样式
    html_content = html_content.replace("</head>", _PDF_STYLE + "</head>")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")
        pdf_bytes = page.pdf(
            landscape=True,
            format="A4",
            margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"},
            print_background=True,
        )
        browser.close()

    return pdf_bytes
