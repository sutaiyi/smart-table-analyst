import re
import pandas as pd
import numpy as np
import traceback


def extract_code(response: str) -> str:
    pattern = r"```python\s*\n(.*?)```"
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()
    # 如果没有代码块标记，尝试整个内容作为代码
    if "import " in response or "result_tables" in response:
        return response.strip()
    raise ValueError("AI返回的内容中未找到Python代码块")


def execute_analysis(
    code: str, df: pd.DataFrame, max_retries: int = 0
) -> dict:
    namespace = {
        "df": df.copy(),
        "pd": pd,
        "np": np,
        "result_tables": {},
        "charts": [],
        "summary": "",
    }

    try:
        exec(code, namespace)  # noqa: S102
    except Exception as e:
        error_msg = f"代码执行出错: {e}\n{traceback.format_exc()}"
        raise RuntimeError(error_msg) from e

    result_tables = namespace.get("result_tables", {})
    charts = namespace.get("charts", [])
    summary = namespace.get("summary", "")

    if not isinstance(result_tables, dict):
        result_tables = {"分析结果": result_tables} if isinstance(result_tables, pd.DataFrame) else {}

    return {
        "result_tables": result_tables,
        "charts": charts,
        "summary": summary,
    }
