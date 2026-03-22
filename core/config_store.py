"""
模型配置的本地持久化。

使用本地 JSON 文件存储，避免 Streamlit 与浏览器 localStorage 的异步通信问题。
同时在页面中注入 JS 同步写入 localStorage，实现浏览器端也有一份配置缓存。
"""
import json
import os
import streamlit.components.v1 as components

_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "model_config.json")


def _ensure_dir():
    os.makedirs(os.path.dirname(_CONFIG_FILE), exist_ok=True)


def load_config() -> dict:
    """加载保存的模型配置"""
    if not os.path.exists(_CONFIG_FILE):
        return {}
    try:
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(base_url: str, api_key: str, model: str):
    """保存模型配置到本地文件，同时同步到浏览器 localStorage"""
    _ensure_dir()
    config = {"base_url": base_url, "api_key": api_key, "model": model}
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # 同步写入浏览器 localStorage
    config_json = json.dumps(config, ensure_ascii=False)
    components.html(
        f"""<script>
        localStorage.setItem('sta_model_config', JSON.stringify({config_json}));
        </script>""",
        height=0,
    )
