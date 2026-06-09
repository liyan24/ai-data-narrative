"""DataAnalysisAgent: Step 2 - Analyze data with type-aware analysis planning."""
from __future__ import annotations

import json
from typing import Any, Dict

from ai_data_narrative.agents.base import Agent
from ai_data_narrative.llm.prompts import DATA_ANALYSIS_SYSTEM
from ai_data_narrative.models import AgentOutput, AgentPlan


ANALYSIS_PLAN_PROMPT = """你是一位资深数据科学家。请基于以下数据信息，充分思考该数据适合进行哪些分析，并制定一个详细的分析计划。

请根据数据类型选择恰当的分析方法：

【多维表格 (Table)】适合的分析方法：
- 描述统计：均值、中位数、标准差、四分位数、极值
- 分布分析：频数分布、直方图、箱线图
- 相关性分析：Pearson/Spearman 相关系数矩阵
- 分组聚合：按分类维度汇总数值指标
- 异常检测：3-sigma、IQR 异常值识别
- 缺失值与重复值分析

【时序数据 (Timeseries)】适合的分析方法：
- 趋势分析：线性/非线性趋势拟合、移动平均
- 季节性分析：周期性检测、季节分解
- 自相关性：ACF/PACF 分析、滞后相关性
- 波动分析：标准差变化、峰度偏度
- 突变点检测：均值/方差突变
- 增长率与同比环比

【网络数据 (Network)】适合的分析方法：
- 基本统计：节点数、边数、平均度、网络直径
- 连通性：连通分量数量、最大连通子图规模、网络密度
- 中心性分析：度中心性、介数中心性、接近中心性、特征向量中心性、PageRank
- 社区发现：模块度、社区划分
- 聚类系数：平均聚类系数、传递性
- 路径分析：平均最短路径长度

【JSON 数据】适合的分析方法：
- 结构分析：嵌套深度、字段覆盖率、 schema 一致性
- 数值统计：数值字段的分布、极值、均值
- 文本统计：字符串长度分布、高频词汇
- 数组分析：数组长度分布、元素类型分布

请用中文回复，并返回包含以下字段的合法 JSON：
- analysis_plan: 分析计划对象，包含：
  - data_type_detected: 检测到的数据类型（table / timeseries / network / json）
  - rationale: 为什么判断为该数据类型
  - methods: 分析方法数组，每项包含 method（方法名）、purpose（分析目的）、expected_output（预期输出）
"""


class DataAnalysisAgent(Agent):
    name = "data_analysis"
    role = "data / network scientist"
    system_prompt = DATA_ANALYSIS_SYSTEM

    def plan(self, context: Dict[str, Any]) -> AgentPlan:
        """First, let LLM think about what analyses are appropriate for this data."""
        data_summary = self._summarize_data(context.get("data"), context.get("data_description", {}))
        user_request = context.get("input", {}).get("user_request", "")

        plan_prompt = f"""{ANALYSIS_PLAN_PROMPT}

【用户请求】：
{user_request}

【数据摘要】：
{data_summary}

请返回分析计划 JSON。"""
        plan_result = self._ask_json(plan_prompt)

        analysis_plan = plan_result.get("analysis_plan", {})
        methods = analysis_plan.get("methods", [])

        steps = ["分析数据类型并制定分析计划", "执行分析计算", "汇总关键发现"]
        if methods:
            steps = ["制定分析计划: " + m["method"] for m in methods[:3]] + ["执行分析计算", "汇总关键发现"]

        return AgentPlan(
            agent_name=self.name,
            goal="计算指标并识别关键发现",
            steps=steps,
            expected_output={
                "findings": "array",
                "code": "string",
                "recommended_charts": "array",
                "analysis_plan": "object",
            },
            parameters={"analysis_plan": analysis_plan, "data_summary": data_summary},
        )

    def execute(self, plan: AgentPlan, context: Dict[str, Any]) -> AgentOutput:
        data_summary = plan.parameters.get("data_summary", self._summarize_data(context.get("data"), context.get("data_description", {})))
        analysis_plan = plan.parameters.get("analysis_plan", {})
        prev = context.get("previous_output", {})
        user_request = context.get("input", {}).get("user_request", "")

        methods_text = json.dumps(analysis_plan.get("methods", []), ensure_ascii=False, indent=2, default=str)
        data_type = analysis_plan.get("data_type_detected", "unknown")
        code_guidance = self._get_code_guidance(data_type, context.get("data"))

        prompt = f"""数据分析任务。

【分析计划】：
数据类型: {data_type}
判断理由: {analysis_plan.get('rationale', '')}

计划执行的分析方法：
{methods_text}

【数据结构详情】：
{data_summary}

【代码生成要求】：
{code_guidance}

【用户请求】：
{user_request}

重要约束：
1. 生成的 Python 代码必须使用注入的 `data` 变量来获取数据，禁止从文件读取。
2. 代码中使用的列名/键名必须来自上面数据结构详情中列出的实际列名，禁止编造不存在的列名。
3. 如果数据是 pandas DataFrame，使用 `df = data`；如果是网络图 dict（nodes+edges），使用 `nodes = data['nodes']`, `edges = data['edges']`；如果是 JSON list，使用原始数据。
4. 代码必须将分析结果赋值给 `result` 变量（dict 格式，键为中文指标名，值为具体数值）。
5. 仅允许使用 pandas、numpy、networkx、matplotlib、scipy、statsmodels。禁止使用 os、subprocess、eval、exec。
6. 所有 findings 的 description 请使用中文。

请用中文回复，并返回包含以下字段的合法 JSON：
- findings: 发现数组，每项包含 metric（指标名）、value（数值）、description（中文描述）
- code: Python 代码字符串
- recommended_charts: 推荐的图表类型数组
"""
        result = self._ask_json(prompt)

        code = result.get("code", "")
        executed_findings = result.get("findings", [])

        if code:
            skill = self.get_skill("data_analysis")
            if skill:
                from ai_data_narrative.models import SkillPlan

                sp = SkillPlan(skill_name="data_analysis", intent="compute metrics", code=code, parameters={})
                skill_result = skill.execute(sp, {"data": context.get("data")})
                result["skill_execution"] = {
                    "success": skill_result.success,
                    "stdout": skill_result.stdout,
                    "stderr": skill_result.stderr,
                    "files": skill_result.files,
                    "return_value": skill_result.return_value,
                }
                if skill_result.success and skill_result.return_value is not None:
                    computed = skill_result.return_value
                    if isinstance(computed, list):
                        executed_findings = computed
                    elif isinstance(computed, dict):
                        executed_findings = [
                            {"metric": str(k), "value": v, "description": f"{k} = {v}"}
                            for k, v in computed.items()
                        ]
                    else:
                        executed_findings = [{"metric": "computed_result", "value": computed, "description": str(computed)}]

        if not executed_findings:
            executed_findings = result.get("findings", [])
        result["findings"] = executed_findings
        result["analysis_plan"] = analysis_plan

        return AgentOutput(
            agent_name=self.name,
            artifacts=result,
            reasoning="已基于数据类型制定分析计划，并优先使用代码执行的真实结果作为 findings。",
        )

    @staticmethod
    def _get_code_guidance(data_type: str, data: Any) -> str:
        """Return comprehensive code templates covering all analysis dimensions."""
        if data_type == "network":
            return _NETWORK_CODE_TEMPLATE
        elif data_type == "timeseries":
            return _TIMESERIES_CODE_TEMPLATE
        elif data_type == "table":
            return _TABLE_CODE_TEMPLATE
        else:
            return _JSON_CODE_TEMPLATE

    @staticmethod
    def _summarize_data(data: Any, data_description: Dict[str, Any]) -> str:
        if data is None:
            return "未提供数据。"
        try:
            import pandas as pd
            import numpy as np

            if isinstance(data, pd.DataFrame):
                desc = data_description or {}
                is_timeseries = False
                for col in data.columns:
                    if pd.api.types.is_datetime64_any_dtype(data[col]):
                        is_timeseries = True
                        break
                    if any(kw in str(col).lower() for kw in ['date', 'time', '日期', '时间', 'timestamp']):
                        is_timeseries = True
                        break

                summary = {
                    "type": "DataFrame",
                    "is_likely_timeseries": is_timeseries,
                    "shape": data.shape,
                    "columns": list(data.columns),
                    "dtypes": {c: str(t) for c, t in data.dtypes.items()},
                    "sample_rows": data.head(3).to_dict(orient="records"),
                    "numeric_summary": json.loads(data.describe().to_json(force_ascii=False)) if not data.empty else {},
                    "metadata": desc,
                }
                return json.dumps(summary, ensure_ascii=False, indent=2, default=str)

            if isinstance(data, dict):
                if "nodes" in data and "edges" in data:
                    nodes = data["nodes"]
                    edges = data["edges"]
                    node_types = {}
                    for n in nodes:
                        node_types[n.get("type", "unknown")] = node_types.get(n.get("type", "unknown"), 0) + 1
                    edge_types = {}
                    for e in edges:
                        edge_types[e.get("type", "unknown")] = edge_types.get(e.get("type", "unknown"), 0) + 1
                    summary = {
                        "type": "network",
                        "node_count": len(nodes),
                        "edge_count": len(edges),
                        "node_types": node_types,
                        "edge_types": edge_types,
                        "sample_nodes": nodes[:2] if nodes else [],
                        "sample_edges": edges[:2] if edges else [],
                        "metadata": data_description or {},
                    }
                    return json.dumps(summary, ensure_ascii=False, indent=2, default=str)
                return json.dumps({k: type(v).__name__ for k, v in data.items()}, ensure_ascii=False)

            if isinstance(data, list):
                summary = {
                    "type": "array",
                    "length": len(data),
                    "sample": data[:2],
                    "metadata": data_description or {},
                }
                return json.dumps(summary, ensure_ascii=False, indent=2, default=str)

            return f"数据类型: {type(data).__name__}"
        except Exception as exc:
            return f"无法汇总数据: {exc}"


# =============================================================================
# Comprehensive code templates - each covers ALL analysis dimensions
# =============================================================================

_NETWORK_CODE_TEMPLATE = """【网络数据代码模板 - 覆盖全部6个分析维度】
```python
import networkx as nx
import pandas as pd
import numpy as np

nodes = data['nodes']
edges = data['edges']
is_directed = any(e.get('directed', False) for e in edges) if edges else False
G = nx.DiGraph() if is_directed else nx.Graph()

for n in nodes:
    nid = n.get('id', n)
    G.add_node(nid, **n.get('attributes', {}))
for e in edges:
    G.add_edge(e['source'], e['target'], **e.get('properties', {}))

result = {}
N = G.number_of_nodes()
M = G.number_of_edges()

# === 维度1: 基本统计 ===
result['节点总数'] = N
result['边总数'] = M
result['平均度'] = round(2 * M / N, 4) if N > 0 else 0
degrees = dict(G.degree())
result['最大度'] = max(degrees.values()) if degrees else 0
result['最小度'] = min(degrees.values()) if degrees else 0

# === 维度2: 连通性 ===
if is_directed:
    comps = list(nx.weakly_connected_components(G))
    result['弱连通分量数'] = len(comps)
    result['最大弱连通子图节点数'] = len(max(comps, key=len)) if comps else 0
else:
    comps = list(nx.connected_components(G))
    result['连通分量数'] = len(comps)
    result['最大连通子图节点数'] = len(max(comps, key=len)) if comps else 0
result['网络密度'] = round(nx.density(G), 4)

# === 维度3: 中心性分析 ===
if N > 0:
    dc = nx.degree_centrality(G)
    result['度中心性_TOP5'] = [{k: round(v, 4)} for k, v in sorted(dc.items(), key=lambda x: -x[1])[:5]]
    
    bc = nx.betweenness_centrality(G)
    result['介数中心性_TOP5'] = [{k: round(v, 4)} for k, v in sorted(bc.items(), key=lambda x: -x[1])[:5]]
    
    if not is_directed:
        cc = nx.closeness_centrality(G)
        result['接近中心性_TOP5'] = [{k: round(v, 4)} for k, v in sorted(cc.items(), key=lambda x: -x[1])[:5]]
        ec = nx.eigenvector_centrality(G, max_iter=1000)
        result['特征向量中心性_TOP5'] = [{k: round(v, 4)} for k, v in sorted(ec.items(), key=lambda x: -x[1])[:5]]
    
    if is_directed:
        pr = nx.pagerank(G)
        result['PageRank_TOP5'] = [{k: round(v, 4)} for k, v in sorted(pr.items(), key=lambda x: -x[1])[:5]]

# === 维度4: 社区发现 ===
if not is_directed and N > 0:
    try:
        comms = list(nx.community.greedy_modularity_communities(G))
        result['社区数量'] = len(comms)
        result['最大社区节点数'] = len(max(comms, key=len)) if comms else 0
        result['模块度'] = round(nx.community.modularity(G, comms), 4)
    except Exception:
        pass

# === 维度5: 聚类系数 ===
if not is_directed and N > 0:
    try:
        result['平均聚类系数'] = round(nx.average_clustering(G), 4)
        result['传递性'] = round(nx.transitivity(G), 4)
    except Exception:
        pass

# === 维度6: 路径分析 ===
if not is_directed and N > 0:
    largest_cc = max(nx.connected_components(G), key=len, default=set())
    if len(largest_cc) > 1:
        subG = G.subgraph(largest_cc)
        try:
            result['平均最短路径长度'] = round(nx.average_shortest_path_length(subG), 4)
            result['网络直径'] = nx.diameter(subG)
        except Exception:
            pass
```"""


_TIMESERIES_CODE_TEMPLATE = """【时序数据代码模板 - 覆盖全部6个分析维度】
```python
import pandas as pd
import numpy as np

df = data

# 自动识别时间列和数值列
time_col = None
numeric_cols = []
for col in df.columns:
    if pd.api.types.is_datetime64_any_dtype(df[col]):
        time_col = col
    elif any(kw in str(col).lower() for kw in ['date', 'time', '日期', '时间', 'timestamp', 'day', 'month', 'year']):
        time_col = col
    elif pd.api.types.is_numeric_dtype(df[col]):
        numeric_cols.append(col)

if time_col:
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    df = df.sort_values(time_col).reset_index(drop=True)

result = {}
result['时间列'] = time_col
result['数值列'] = numeric_cols
result['记录数'] = len(df)

for col in numeric_cols[:5]:
    s = df[col].dropna()
    if len(s) == 0:
        continue
    
    # === 维度1: 描述统计 ===
    result[f'{col}_均值'] = round(s.mean(), 4)
    result[f'{col}_标准差'] = round(s.std(), 4)
    result[f'{col}_最小值'] = round(s.min(), 4)
    result[f'{col}_最大值'] = round(s.max(), 4)
    result[f'{col}_中位数'] = round(s.median(), 4)
    
    # === 维度2: 趋势分析 ===
    if len(s) >= 2:
        x = np.arange(len(s))
        slope = np.polyfit(x, s.values, 1)[0]
        result[f'{col}_趋势斜率'] = round(slope, 4)
        result[f'{col}_总增长率'] = round((s.iloc[-1] - s.iloc[0]) / s.iloc[0] * 100, 4) if s.iloc[0] != 0 else 0
    
    for window in [3, 7, 30]:
        if len(s) >= window:
            ma = s.rolling(window=window).mean().iloc[-1]
            result[f'{col}_MA{window}'] = round(ma, 4)
    
    # === 维度3: 季节性/周期性 ===
    if len(s) >= 4:
        # 月度均值（如果有时间列）
        if time_col and time_col in df.columns:
            try:
                monthly = df.set_index(time_col)[col].resample('ME').mean().dropna()
                if len(monthly) >= 2:
                    result[f'{col}_月度均值变化'] = round((monthly.iloc[-1] - monthly.iloc[0]) / monthly.iloc[0] * 100, 4) if monthly.iloc[0] != 0 else 0
            except Exception:
                pass
    
    # === 维度4: 自相关性 ===
    if len(s) > 1:
        acf_lags = {}
        for lag in [1, 2, 3, 7]:
            if len(s) > lag:
                acf_lags[f'lag{lag}'] = round(s.autocorr(lag=lag), 4)
        result[f'{col}_自相关系数'] = acf_lags
    
    # === 维度5: 波动分析 ===
    result[f'{col}_偏度'] = round(s.skew(), 4)
    result[f'{col}_峰度'] = round(s.kurtosis(), 4)
    if len(s) >= 7:
        rolling_std = s.rolling(window=7).std().dropna()
        result[f'{col}_7期滚动标准差_均值'] = round(rolling_std.mean(), 4)
        result[f'{col}_7期滚动标准差_最大'] = round(rolling_std.max(), 4)
    
    # === 维度6: 突变点检测 (简单 CUSUM) ===
    if len(s) >= 10:
        mean_val = s.mean()
        cusum_pos = np.maximum.accumulate(np.cumsum(s.values - mean_val))
        cusum_neg = np.minimum.accumulate(np.cumsum(s.values - mean_val))
        result[f'{col}_CUSUM正向最大偏差'] = round(float(cusum_pos.max()), 4)
        result[f'{col}_CUSUM负向最大偏差'] = round(float(abs(cusum_neg.min())), 4)
```"""


_TABLE_CODE_TEMPLATE = """【表格数据代码模板 - 覆盖全部6个分析维度】
```python
import pandas as pd
import numpy as np

df = data
result = {}

# === 维度1: 描述统计 ===
result['行数'] = len(df)
result['列数'] = len(df.columns)
result['列名'] = list(df.columns)

numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()

result['数值列'] = numeric_cols
result['分类列'] = cat_cols
result['时间列'] = datetime_cols

# 所有数值列的完整描述统计
for col in numeric_cols:
    s = df[col].dropna()
    if len(s) == 0:
        continue
    result[f'{col}_计数'] = int(s.count())
    result[f'{col}_均值'] = round(s.mean(), 4)
    result[f'{col}_标准差'] = round(s.std(), 4)
    result[f'{col}_最小值'] = round(s.min(), 4)
    result[f'{col}_25分位'] = round(s.quantile(0.25), 4)
    result[f'{col}_中位数'] = round(s.quantile(0.50), 4)
    result[f'{col}_75分位'] = round(s.quantile(0.75), 4)
    result[f'{col}_最大值'] = round(s.max(), 4)
    result[f'{col}_极差'] = round(s.max() - s.min(), 4)

# === 维度2: 分布分析 ===
for col in numeric_cols:
    s = df[col].dropna()
    if len(s) == 0:
        continue
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = s[(s < lower) | (s > upper)]
    result[f'{col}_IQR异常值数量'] = int(len(outliers))
    result[f'{col}_IQR异常值比例'] = round(len(outliers) / len(s) * 100, 2)

# === 维度3: 相关性分析 ===
if len(numeric_cols) >= 2:
    corr_matrix = df[numeric_cols].corr()
    corr_pairs = []
    for i in range(len(numeric_cols)):
        for j in range(i + 1, len(numeric_cols)):
            corr_pairs.append((numeric_cols[i], numeric_cols[j], round(corr_matrix.iloc[i, j], 4)))
    corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    result['相关性矩阵'] = corr_matrix.round(4).to_dict()
    result['最强正相关'] = corr_pairs[0] if corr_pairs and corr_pairs[0][2] > 0 else None
    result['最强负相关'] = next((p for p in corr_pairs if p[2] < 0), None)

# === 维度4: 分组聚合 ===
for cat_col in cat_cols[:3]:
    for num_col in numeric_cols[:3]:
        try:
            grouped = df.groupby(cat_col)[num_col].agg(['mean', 'sum', 'count']).round(4)
            result[f'{cat_col}分组_{num_col}_均值TOP3'] = grouped.sort_values('mean', ascending=False).head(3).to_dict()
        except Exception:
            pass

# === 维度5: 异常检测 (3-sigma) ===
for col in numeric_cols:
    s = df[col].dropna()
    if len(s) == 0:
        continue
    mean = s.mean()
    std = s.std()
    if std > 0:
        outliers_3sigma = s[(s < mean - 3 * std) | (s > mean + 3 * std)]
        result[f'{col}_3Sigma异常值数量'] = int(len(outliers_3sigma))

# === 维度6: 缺失值与重复值 ===
missing = df.isnull().sum()
result['缺失值总单元格数'] = int(missing.sum())
result['缺失值列统计'] = {col: int(v) for col, v in missing.items() if v > 0}
result['重复行数'] = int(df.duplicated().sum())
result['重复行比例'] = round(df.duplicated().sum() / len(df) * 100, 2) if len(df) > 0 else 0
```"""


_JSON_CODE_TEMPLATE = """【JSON数据代码模板 - 覆盖全部4个分析维度】
```python
import pandas as pd
import numpy as np

result = {}

# === 维度1: 结构分析 ===
def analyze_structure(obj, depth=0):
    info = {'depth': depth, 'type': type(obj).__name__}
    if isinstance(obj, dict):
        info['keys'] = list(obj.keys())
        info['key_count'] = len(obj)
        for k, v in obj.items():
            child = analyze_structure(v, depth + 1)
            info[f'{k}_depth'] = child['depth']
    elif isinstance(obj, list):
        info['length'] = len(obj)
        if obj:
            info['item_type'] = type(obj[0]).__name__
            info['first_item_depth'] = analyze_structure(obj[0], depth + 1)['depth']
    return info

if isinstance(data, list) and data:
    result['记录总数'] = len(data)
    result['首条记录结构'] = analyze_structure(data[0])
    
    # 收集所有键
    all_keys = set()
    for item in data:
        if isinstance(item, dict):
            all_keys.update(item.keys())
    result['所有字段名'] = list(all_keys)
    
    # 字段覆盖率
    coverage = {}
    for key in all_keys:
        count = sum(1 for item in data if isinstance(item, dict) and key in item and item[key] is not None)
        coverage[key] = {'出现次数': count, '覆盖率': round(count / len(data) * 100, 2)}
    result['字段覆盖率'] = coverage
    
    # === 维度2: 数值统计 ===
    for key in all_keys:
        values = []
        for item in data:
            if isinstance(item, dict) and key in item:
                v = item[key]
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    values.append(v)
        if values:
            arr = np.array(values)
            result[f'{key}_数值统计'] = {
                '计数': int(len(arr)),
                '均值': round(float(arr.mean()), 4),
                '标准差': round(float(arr.std()), 4),
                '最小值': round(float(arr.min()), 4),
                '最大值': round(float(arr.max()), 4),
                '中位数': round(float(np.median(arr)), 4),
            }
    
    # === 维度3: 文本统计 ===
    for key in all_keys:
        texts = []
        for item in data:
            if isinstance(item, dict) and key in item and isinstance(item[key], str):
                texts.append(item[key])
        if texts:
            lengths = [len(t) for t in texts]
            result[f'{key}_文本统计'] = {
                '文本记录数': len(texts),
                '平均长度': round(sum(lengths) / len(lengths), 2),
                '最大长度': max(lengths),
                '最小长度': min(lengths),
            }
    
    # === 维度4: 数组分析 ===
    for key in all_keys:
        arrays = []
        for item in data:
            if isinstance(item, dict) and key in item and isinstance(item[key], list):
                arrays.append(item[key])
        if arrays:
            lengths = [len(a) for a in arrays]
            result[f'{key}_数组统计'] = {
                '数组记录数': len(arrays),
                '平均长度': round(sum(lengths) / len(lengths), 2),
                '最大长度': max(lengths),
                '最小长度': min(lengths),
            }

elif isinstance(data, dict):
    result['根对象类型'] = 'dict'
    result['根对象键数'] = len(data)
    result['根对象结构'] = analyze_structure(data)
else:
    result['数据类型'] = type(data).__name__
    result['数据长度'] = len(data) if hasattr(data, '__len__') else 'N/A'
```"""
