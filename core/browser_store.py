"""
浏览器端存储（localStorage）。
- 写入：用 components.html(height=0) 注入 JS，无视觉影响
- 读取：用 streamlit_js_eval 在 session 启动时读取一次，之后全走 session_state
"""
import json
import time

import streamlit as st
import streamlit.components.v1 as components
from streamlit_js_eval import streamlit_js_eval

_CONFIG_KEY = "sta_model_config"
_HISTORY_KEY = "sta_history"
_MAX_HISTORY = 50


# ═══════════════════════════════════════════
#  初始化：从浏览器 localStorage 加载到 session_state
# ═══════════════════════════════════════════
def init_browser_store():
    """
    在 session 启动时调用一次。
    从 localStorage 读取 config 和 history 到 session_state。
    streamlit_js_eval 第一次渲染返回 None（JS 尚未执行），
    第二次渲染返回实际值。用 _browser_loaded 标记是否已成功加载。
    """
    if st.session_state.get("_browser_loaded"):
        return  # 已加载过，跳过

    # 初始化默认值（确保即使 JS 失败也能正常运行）
    if "browser_config" not in st.session_state:
        st.session_state["browser_config"] = {}
    if "browser_history" not in st.session_state:
        st.session_state["browser_history"] = []

    # 尝试从 localStorage 读取
    try:
        config_raw = streamlit_js_eval(
            js_expressions=f"localStorage.getItem('{_CONFIG_KEY}')",
            key="_load_config",
        )
        history_raw = streamlit_js_eval(
            js_expressions=f"localStorage.getItem('{_HISTORY_KEY}')",
            key="_load_history",
        )
    except Exception:
        # JS eval 失败，用默认值继续
        st.session_state["_browser_loaded"] = True
        return

    # 第一次渲染返回 None（JS 尚未执行），标记为已加载，用默认值先跑
    # 如果后续 rerun 拿到了真实值会自动更新
    if config_raw is not None and isinstance(config_raw, str):
        try:
            st.session_state["browser_config"] = json.loads(config_raw)
        except json.JSONDecodeError:
            pass

    if history_raw is not None and isinstance(history_raw, str):
        try:
            st.session_state["browser_history"] = json.loads(history_raw)
        except json.JSONDecodeError:
            pass

    # 无论是否拿到值，都标记为已加载，不阻塞页面
    st.session_state["_browser_loaded"] = True


def is_loaded() -> bool:
    return st.session_state.get("_browser_loaded", False)


# ═══════════════════════════════════════════
#  写入 localStorage（静默，无视觉影响）
# ═══════════════════════════════════════════
def _write_to_ls(key: str, data):
    """将数据写入浏览器 localStorage"""
    json_str = json.dumps(data, ensure_ascii=False, default=str)
    # 转义单引号和反斜杠
    safe_str = json_str.replace("\\", "\\\\").replace("'", "\\'")
    components.html(
        f"<script>localStorage.setItem('{key}', '{safe_str}');</script>",
        height=0,
    )


# ═══════════════════════════════════════════
#  模型配置
# ═══════════════════════════════════════════
def get_config() -> dict:
    return st.session_state.get("browser_config", {})


def save_config(base_url: str, api_key: str, model: str):
    config = {"base_url": base_url, "api_key": api_key, "model": model}
    st.session_state["browser_config"] = config
    _write_to_ls(_CONFIG_KEY, config)


# ═══════════════════════════════════════════
#  历史记录
# ═══════════════════════════════════════════
def get_history() -> list[dict]:
    return st.session_state.get("browser_history", [])


def save_history(record: dict):
    history = get_history().copy()
    history.insert(0, record)
    history = history[:_MAX_HISTORY]
    st.session_state["browser_history"] = history
    _write_to_ls(_HISTORY_KEY, history)


def delete_history(record_id: int):
    history = [r for r in get_history() if r.get("id") != record_id]
    st.session_state["browser_history"] = history
    _write_to_ls(_HISTORY_KEY, history)


def update_history(record_id: int, updates: dict):
    history = get_history().copy()
    for rec in history:
        if rec.get("id") == record_id:
            rec.update(updates)
            break
    st.session_state["browser_history"] = history
    _write_to_ls(_HISTORY_KEY, history)


def clear_history():
    st.session_state["browser_history"] = []
    _write_to_ls(_HISTORY_KEY, [])
