import io
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def export_excel(result_tables: dict[str, pd.DataFrame], summary: str = "") -> bytes:
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # 写入摘要页
        if summary:
            summary_df = pd.DataFrame({"分析摘要": [summary]})
            summary_df.to_excel(writer, sheet_name="摘要", index=False)

        # 写入各结果表
        for title, df in result_tables.items():
            sheet_name = title[:31]  # Excel sheet名最长31字符
            df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)

            ws = writer.sheets[sheet_name]

            # 添加标题行
            ws.cell(row=1, column=1, value=title).font = Font(
                bold=True, size=14, color="1F4E79"
            )

            # 设置表头样式
            header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=11)
            thin_border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin"),
            )

            for col_idx, col_name in enumerate(df.columns, 1):
                cell = ws.cell(row=2, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")
                cell.border = thin_border

            # 设置数据区域样式和列宽
            for col_idx in range(1, len(df.columns) + 1):
                max_width = len(str(df.columns[col_idx - 1]))
                for row_idx in range(3, len(df) + 3):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    cell.border = thin_border
                    cell.alignment = Alignment(horizontal="center")
                    val_len = len(str(cell.value or ""))
                    if val_len > max_width:
                        max_width = val_len

                col_letter = get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = min(max_width + 4, 40)

    return buffer.getvalue()
