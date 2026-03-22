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
   - `result_tables`: dict[str, pd.DataFrame] — 分析结果表格，key为表格标题。
     **重要：分组数据请确保按分组列排序，系统会自动合并显示连续相同值的单元格。**
     例如按部门分组统计时，确保同一部门的行连续排列。
   - `charts`: list[dict] — 图表配置列表。**默认为空列表 `charts = []`。**
     **禁止自动生成图表。** 只有当用户的需求中明确包含"图表"、"柱状图"、"折线图"、"饼图"、"可视化"、"图形"等图表相关关键词时才生成。
     如果用户只说了"分析"、"统计"、"汇总"等，一律不生成图表。
     如果用户要求了图表，每个dict包含:
     - `title`: 图表标题
     - `type`: 图表类型 (bar/line/pie/scatter/heatmap)
     - `data`: 绘图所需的DataFrame
     - `x`: X轴列名 (可选)
     - `y`: Y轴列名或列名列表 (可选)
     - `labels`: 标签列名 (饼图用, 可选)
     - `values`: 值列名 (饼图用, 可选)
   - `summary`: str — 分析结论摘要（支持Markdown格式）
3. **严格按照用户的分析要求执行，不要添加用户没有要求的内容（如用户没要求图表就不生成图表，没要求小计就不加小计）**
4. 只输出Python代码块，不要解释
5. 代码中可以使用 pandas 和 numpy
6. 确保代码健壮，处理可能的空值和类型问题
7. 日期列转换时务必使用 errors='coerce' 参数，如: pd.to_datetime(df['col'], errors='coerce')
8. 数值列转换时同样使用 errors='coerce'，如: pd.to_numeric(df['col'], errors='coerce')
9. 分析前先用 df.dropna(subset=[关键列]) 过滤掉关键字段为空的行
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


SYSTEM_PROMPT_REVISE = """你是一个Python数据分析专家。用户之前已经完成了一次分析，现在希望对结果进行修改。

你需要根据用户的修改意见，在原有代码的基础上进行调整，输出修改后的**完整Python代码**。

要求：
1. 输入变量 `df` 是已加载的pandas DataFrame
2. 代码必须生成以下变量：
   - `result_tables`: dict[str, pd.DataFrame] — 分析结果表格。分组数据请确保按分组列排序。
   - `charts`: list[dict] — 图表配置列表（title/type/data/x/y/labels/values）
   - `summary`: str — 分析结论摘要
3. 只输出Python代码块，不要解释
4. 保留原有分析中用户未要求修改的部分
5. 日期列转换用 errors='coerce'，数值列同理
"""


def build_revise_messages(
    user_feedback: str,
    previous_code: str,
    data_summary: str,
    conversation_history: list[dict] | None = None,
) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT_REVISE}]

    # 加入之前的对话历史，保持上下文连贯
    if conversation_history:
        messages.extend(conversation_history)

    messages.append({
        "role": "user",
        "content": (
            f"## 数据概况\n{data_summary}\n\n"
            f"## 上一次的分析代码\n```python\n{previous_code}\n```\n\n"
            f"## 修改意见\n{user_feedback}\n\n"
            "请输出修改后的完整Python代码。"
        ),
    })
    return messages
