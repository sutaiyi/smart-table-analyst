SYSTEM_PROMPT_REFINE = """你是一个专业的数据分析助手。用户会上传一个表格数据并描述分析需求。
你的任务是将用户的模糊需求转化为一个**结构化的分析提示词**，方便后续AI执行精确分析。

请按以下格式输出：

## 分析目标
（简明描述分析的核心目的）

## 分析维度
（列出需要分析的维度/字段）

## 分析步骤
（编号列出具体步骤）

## 输出要求
- 需要生成的表格（描述表格结构）
- 需要生成的图表（类型、X轴、Y轴）

## 注意事项
（数据处理的特殊要求）
"""

SYSTEM_PROMPT_ANALYZE = """你是一个Python数据分析专家。根据用户的分析需求，编写Python代码来分析pandas DataFrame。

要求：
1. 输入变量 `df` 是已加载的pandas DataFrame
2. 代码必须生成以下变量：
   - `result_tables`: dict[str, pd.DataFrame] — 分析结果表格，key为表格标题
   - `charts`: list[dict] — 图表配置列表，每个dict包含:
     - `title`: 图表标题
     - `type`: 图表类型 (bar/line/pie/scatter/heatmap)
     - `data`: 绘图所需的DataFrame
     - `x`: X轴列名 (可选)
     - `y`: Y轴列名或列名列表 (可选)
     - `labels`: 标签列名 (饼图用, 可选)
     - `values`: 值列名 (饼图用, 可选)
   - `summary`: str — 分析结论摘要（支持Markdown格式）
3. 只输出Python代码块，不要解释
4. 代码中可以使用 pandas 和 numpy
5. 确保代码健壮，处理可能的空值和类型问题
"""


def build_refine_messages(user_request: str, data_summary: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT_REFINE},
        {
            "role": "user",
            "content": f"## 数据概况\n{data_summary}\n\n## 用户需求\n{user_request}",
        },
    ]


def build_analyze_messages(
    confirmed_prompt: str, data_summary: str
) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT_ANALYZE},
        {
            "role": "user",
            "content": (
                f"## 数据概况\n{data_summary}\n\n"
                f"## 分析要求\n{confirmed_prompt}\n\n"
                "请编写完整的Python分析代码。"
            ),
        },
    ]
