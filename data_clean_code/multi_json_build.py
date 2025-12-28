import pandas as pd
import json

# ======================
# 基本配置（基于 cleaned_data.csv 实际字段）
# ======================
csv_path = "cleaned_data.csv"

city_col = "工作城市"        # 城市列
direction_col = "主要AI方向"  # 当作“岗位类别/方向”节点用

exp_col = "经验段"
degree_col = "学历层级"
salary_col = "中位月薪_元"   # 若你想用平均薪资，改成对应列名即可

# ======================
# 读取数据
# ======================
df = pd.read_csv(csv_path)

# 统一类型
for col in [city_col, direction_col, exp_col, degree_col]:
    df[col] = df[col].astype(str)

df[salary_col] = pd.to_numeric(df[salary_col], errors="coerce")

# ============================================================
# ① 城市 → 主要AI方向 桑基图数据
#    输出: city_direction_sankey.json
# ============================================================
sankey_df = (
    df[[city_col, direction_col]]
    .dropna()
    .groupby([city_col, direction_col])
    .size()
    .reset_index(name="count")
)

# 节点：城市 + 方向
cities = sankey_df[city_col].unique().tolist()
directions = sankey_df[direction_col].unique().tolist()

nodes = [{"name": name} for name in (cities + directions)]

links = []
for _, row in sankey_df.iterrows():
    links.append({
        "source": row[city_col],
        "target": row[direction_col],
        "value": int(row["count"])
    })

sankey_json = {
    "nodes": nodes,
    "links": links
}

with open("city_direction_sankey.json", "w", encoding="utf-8") as f:
    json.dump(sankey_json, f, ensure_ascii=False, indent=2)

print("Saved: city_direction_sankey.json")

# ============================================================
# ② 经验 × 薪资 × 学历 三维气泡图数据
#    X: 经验段
#    Y: 平均薪资
#    颜色: 学历层级
#    气泡大小: 岗位数量
#
#    输出: exp_degree_salary_bubble.json
# ============================================================
bubble_df = (
    df[[exp_col, degree_col, salary_col]]
    .dropna()
    .groupby([exp_col, degree_col])[salary_col]
    .agg(["count", "mean"])
    .reset_index()
)

bubble_df.rename(columns={"count": "cnt", "mean": "avg_salary"}, inplace=True)

# 记录经验段和学历层级的顺序（前端如果想自定义排序可以用这个）
exp_levels = df[exp_col].dropna().unique().tolist()
degree_levels = df[degree_col].dropna().unique().tolist()

bubble_data = []
for _, row in bubble_df.iterrows():
    bubble_data.append({
        "exp": row[exp_col],                          # 经验段
        "degree": row[degree_col],                    # 学历层级
        "avg_salary": round(float(row["avg_salary"]), 2),
        "count": int(row["cnt"])
    })

bubble_json = {
    "exp_levels": exp_levels,
    "degree_levels": degree_levels,
    "data": bubble_data
}

with open("exp_degree_salary_bubble.json", "w", encoding="utf-8") as f:
    json.dump(bubble_json, f, ensure_ascii=False, indent=2)

print("Saved: exp_degree_salary_bubble.json")
