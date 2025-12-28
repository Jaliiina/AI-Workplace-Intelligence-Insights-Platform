import pandas as pd
import json
import collections
import itertools
import math

# ========= 基本配置 =========
csv_path = "cleaned_data.csv"   # 源数据文件
skill_col = "核心技能列表"       # 技能列名
top_n_for_rank = 10            # TopN 排行榜
top_n_for_graph = 30           # 共现图只保留前 N 个技能
min_cooccurrence = 5           # 共现图边权阈值，太小会很吵

# ========= 读数据 & 拆技能 =========
df = pd.read_csv(csv_path)

# 过滤为空的
skills_series = df[skill_col].dropna().astype(str)

def split_skills(s: str):
    """
    把一条岗位的技能字符串拆成列表：
    例如：'Python、机器学习、SQL' -> ['Python', '机器学习', 'SQL']
    如果你后面想换分隔符，只改这里就行
    """
    return [item.strip() for item in s.split("、") if item.strip()]

# 每行岗位的技能列表
all_skill_lists = [split_skills(s) for s in skills_series]

# ========= ⑲ 技能 Top10 排行榜 → skills_top10.json =========
skill_counter = collections.Counter()
for skill_list in all_skill_lists:
    skill_counter.update(skill_list)

# TopN
top_skills_rank = skill_counter.most_common(top_n_for_rank)

skills = [name for name, cnt in top_skills_rank]
counts = [int(cnt) for name, cnt in top_skills_rank]
data = [{"name": name, "value": int(cnt)} for name, cnt in top_skills_rank]

skills_top10_json = {
    # 方便柱状图/条形图：x 轴和 y 数据
    "skills": skills,
    "counts": counts,
    # 方便饼图/排行榜组件：[{name, value}]
    "data": data
}

with open("skills_top10.json", "w", encoding="utf-8") as f:
    json.dump(skills_top10_json, f, ensure_ascii=False, indent=2)

print("Saved: skills_top10.json")

# ========= ⑳ 技能共现关系图 → skills_graph.json =========
# 只取频数最高的前 N 个技能，避免图太乱
top_skills_for_graph = [name for name, _ in skill_counter.most_common(top_n_for_graph)]
top_skill_set = set(top_skills_for_graph)

# 统计共现次数：同一个岗位里同时出现的技能对
co_counter = collections.Counter()

for skill_list in all_skill_lists:
    # 只保留 TopN 里的技能
    filtered = [s for s in skill_list if s in top_skill_set]
    # 去重后做两两组合
    filtered = sorted(set(filtered))
    if len(filtered) < 2:
        continue
    for a, b in itertools.combinations(filtered, 2):
        co_counter[(a, b)] += 1

# 按阈值过滤边
edges = [
    (a, b, w)
    for (a, b), w in co_counter.items()
    if w >= min_cooccurrence
]

# 构建节点：用频数作为 value，用 log 或幂次控制大小别太夸张
max_count = max(skill_counter[s] for s in top_skills_for_graph) if top_skills_for_graph else 1

nodes = []
for name in top_skills_for_graph:
    cnt = int(skill_counter[name])
    # 控制节点尺寸：10 ~ 30 之间
    # size ≈ 10 + 20 * (频数 / 最大频数) ^ 0.6
    ratio = cnt / max_count if max_count > 0 else 0
    symbol_size = 10 + 20 * (ratio ** 0.6)

    nodes.append({
        "id": name,          # ECharts 允许 id/name 同名
        "name": name,
        "value": cnt,        # 节点权重，可以用在 tooltip 里
        "symbolSize": round(symbol_size, 2)
    })

links = []
for a, b, w in edges:
    links.append({
        "source": a,
        "target": b,
        "value": int(w)      # 边权，共现次数
    })

skills_graph_json = {
    "nodes": nodes,
    "links": links
    # 如果你以后想做分类，可以再加 "categories": [...]
}

with open("skills_graph.json", "w", encoding="utf-8") as f:
    json.dump(skills_graph_json, f, ensure_ascii=False, indent=2)

print("Saved: skills_graph.json")
