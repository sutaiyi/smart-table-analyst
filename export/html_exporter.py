import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from jinja2 import Template


def _build_chart(chart_config: dict) -> str:
    chart_type = chart_config.get("type", "bar")
    data = chart_config.get("data")
    title = chart_config.get("title", "")

    if data is None or (isinstance(data, pd.DataFrame) and data.empty):
        return ""

    fig = None
    x = chart_config.get("x")
    y = chart_config.get("y")

    if chart_type == "bar":
        fig = px.bar(data, x=x, y=y, title=title)
    elif chart_type == "line":
        fig = px.line(data, x=x, y=y, title=title)
    elif chart_type == "pie":
        labels = chart_config.get("labels")
        values = chart_config.get("values")
        fig = px.pie(data, names=labels, values=values, title=title)
    elif chart_type == "scatter":
        fig = px.scatter(data, x=x, y=y, title=title)
    elif chart_type == "heatmap":
        fig = px.imshow(data, title=title, text_auto=True, aspect="auto")
    else:
        fig = px.bar(data, x=x, y=y, title=title)

    if fig:
        fig.update_layout(
            template="plotly_white",
            title_font_size=16,
            margin=dict(l=40, r=40, t=60, b=40),
        )
        return fig.to_html(full_html=False, include_plotlyjs=False)
    return ""


def export_html(
    result_tables: dict[str, pd.DataFrame],
    charts: list[dict],
    summary: str = "",
    title: str = "数据分析报告",
    styled_tables: dict[str, str] | None = None,
) -> str:
    css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "style.css")
    with open(css_path, encoding="utf-8") as f:
        css = f.read()

    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "report.html")
    with open(template_path, encoding="utf-8") as f:
        template = Template(f.read())

    chart_htmls = []
    for chart_config in charts:
        html = _build_chart(chart_config)
        if html:
            chart_htmls.append(html)

    styled = styled_tables or {}
    tables = []
    for tbl_title, df in result_tables.items():
        if tbl_title in styled:
            table_html = styled[tbl_title]
        else:
            table_html = df.to_html(
                classes="data-table",
                index=False,
                border=0,
                na_rep="-",
            )
        tables.append((tbl_title, table_html))

    return template.render(
        title=title,
        css=css,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        summary=summary,
        chart_htmls=chart_htmls,
        tables=tables,
    )
