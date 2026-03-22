import re
import importlib
import traceback

import pandas as pd
import numpy as np

# AI生成的代码可能用到的常用库，预加载到执行环境
_OPTIONAL_LIBS = {
    "sklearn": "scikit-learn",
    "scipy": "scipy",
    "statsmodels": "statsmodels",
}


def _try_import(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def extract_code(response: str) -> str:
    pattern = r"```python\s*\n(.*?)```"
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()
    # 如果没有代码块标记，尝试整个内容作为代码
    if "import " in response or "result_tables" in response:
        return response.strip()
    raise ValueError("AI返回的内容中未找到Python代码块")


def _build_namespace(df: pd.DataFrame) -> dict:
    namespace = {
        "df": df.copy(),
        "pd": pd,
        "np": np,
        "result_tables": {},
        "styled_tables": {},
        "charts": [],
        "summary": "",
    }
    for lib_name in _OPTIONAL_LIBS:
        mod = _try_import(lib_name)
        if mod:
            namespace[lib_name] = mod
    return namespace


def execute_analysis(
    code: str, df: pd.DataFrame, llm_client=None, max_retries: int = 2
) -> dict:
    last_error = None

    for attempt in range(max_retries + 1):
        namespace = _build_namespace(df)
        try:
            exec(code, namespace)  # noqa: S102
            break
        except Exception as e:
            last_error = f"{e}\n{traceback.format_exc()}"

            # 最后一次重试仍失败，抛出异常
            if attempt >= max_retries or llm_client is None:
                raise RuntimeError(f"代码执行出错: {last_error}") from e

            # 让 AI 修复代码
            fix_messages = [
                {
                    "role": "system",
                    "content": (
                        "你之前生成的Python数据分析代码执行出错了。"
                        "请根据错误信息修复代码，只输出修复后的完整Python代码块。"
                        "不要解释，只输出```python ... ```代码块。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"## 原始代码\n```python\n{code}\n```\n\n"
                        f"## 错误信息\n```\n{last_error}\n```\n\n"
                        f"## DataFrame信息\n"
                        f"列名: {list(df.columns)}\n"
                        f"形状: {df.shape}\n"
                        f"类型:\n{df.dtypes.to_string()}\n\n"
                        "请输出修复后的完整代码。"
                    ),
                },
            ]
            try:
                response = llm_client.chat(fix_messages, temperature=0.1)
                code = extract_code(response)
            except Exception:
                raise RuntimeError(f"代码执行出错: {last_error}") from e

    result_tables = namespace.get("result_tables", {})
    styled_tables = namespace.get("styled_tables", {})
    charts = namespace.get("charts", [])
    summary = namespace.get("summary", "")

    if not isinstance(result_tables, dict):
        result_tables = {"分析结果": result_tables} if isinstance(result_tables, pd.DataFrame) else {}
    if not isinstance(styled_tables, dict):
        styled_tables = {}

    return {
        "result_tables": result_tables,
        "styled_tables": styled_tables,
        "charts": charts,
        "summary": summary,
    }
