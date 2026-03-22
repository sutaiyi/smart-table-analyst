import pandas as pd
import chardet
import io


def detect_encoding(file_bytes: bytes) -> str:
    result = chardet.detect(file_bytes)
    return result.get("encoding", "utf-8") or "utf-8"


def load_table(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    raw = uploaded_file.getvalue()

    if name.endswith(".csv"):
        encoding = detect_encoding(raw)
        return pd.read_csv(io.BytesIO(raw), encoding=encoding)
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(raw))
    else:
        raise ValueError(f"不支持的文件格式: {name}")


def get_data_summary(df: pd.DataFrame) -> str:
    lines = [
        f"行数: {len(df)}, 列数: {len(df.columns)}",
        f"列名及类型:",
    ]
    for col in df.columns:
        dtype = df[col].dtype
        non_null = df[col].notna().sum()
        unique = df[col].nunique()
        lines.append(f"  - {col} ({dtype}): {non_null}个非空值, {unique}个唯一值")

    lines.append(f"\n前5行数据:\n{df.head().to_string()}")

    # 数值列统计
    numeric_cols = df.select_dtypes(include="number").columns
    if len(numeric_cols) > 0:
        lines.append(f"\n数值列统计:\n{df[numeric_cols].describe().to_string()}")

    return "\n".join(lines)
