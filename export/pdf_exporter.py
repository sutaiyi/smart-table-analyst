import pandas as pd
from weasyprint import HTML, CSS

from .html_exporter import export_html

# PDF 专用样式：横向A4、缩小字号、表格自适应
_PDF_CSS = CSS(string="""
@page {
    size: A4 landscape;
    margin: 12mm;
}
body {
    font-size: 10px;
    background: white;
}
.report-container {
    max-width: 100%;
    padding: 0;
}
.report-header {
    padding: 20px;
    margin-bottom: 15px;
    border-radius: 6px;
}
.report-header h1 { font-size: 20px; }
.summary-card, .chart-section, .table-section {
    padding: 15px;
    margin-bottom: 12px;
    border-radius: 6px;
    box-shadow: none;
    page-break-inside: avoid;
}
table {
    font-size: 9px;
    word-break: break-all;
    table-layout: auto;
    width: 100%;
}
thead th {
    padding: 5px 4px;
    font-size: 9px;
}
tbody td {
    padding: 4px 4px;
    font-size: 9px;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 150px;
}
""")


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
    # 移除plotly js引用（PDF不支持JS）
    html_content = html_content.replace(
        '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>', ""
    )

    pdf_bytes = HTML(string=html_content).write_pdf(stylesheets=[_PDF_CSS])
    return pdf_bytes
