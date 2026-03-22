import pandas as pd
from weasyprint import HTML

from .html_exporter import export_html


def export_pdf(
    result_tables: dict[str, pd.DataFrame],
    charts: list[dict],
    summary: str = "",
    title: str = "数据分析报告",
) -> bytes:
    # 生成不依赖外部plotly.js的HTML（图表转为静态图片）
    html_content = export_html(
        result_tables=result_tables,
        charts=charts,
        summary=summary,
        title=title,
    )
    # 移除plotly js引用（PDF不支持JS），图表以静态方式呈现
    html_content = html_content.replace(
        '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>', ""
    )

    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes
