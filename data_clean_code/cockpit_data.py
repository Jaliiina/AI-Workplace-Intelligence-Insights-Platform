import pandas as pd
import numpy as np
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

# 基础路径 & 读数据
BASE_DIR = Path(__file__).resolve().parent
csv_path = BASE_DIR / "cleaned_data.csv"

df = pd.read_csv(csv_path)

# 必要字段检查
required_cols = ["工作城市", "主要AI方向", "学历层级", "经验段", "中位月薪_元", "核心技能列表"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise SystemExit(f"缺少必要字段: {missing}")

# 拆技能
def split_skills(text: str):
    if not isinstance(text, str):
        return []
    parts = re.split(r"[、，,;/\s]+", text)
    return [p.strip() for p in parts if p.strip()]

df["skills_list"] = df["核心技能列表"].apply(split_skills)

# 构建岗位列表 jobs：前端可以直接用这个做筛选
jobs = []
for idx, row in df.iterrows():
    city = row["工作城市"]
    direction = row["主要AI方向"]
    degree = row["学历层级"]
    exp = row["经验段"]
    salary = row["中位月薪_元"]

    # 没有薪资就先跳过，不参与 gauge
    if pd.isna(salary):
        continue

    jobs.append({
        "id": int(idx),
        "city": None if pd.isna(city) else str(city),
        "direction": None if pd.isna(direction) else str(direction),
        "degree": None if pd.isna(degree) else str(degree),
        "exp": None if pd.isna(exp) else str(exp),
        "salary": float(salary),
        "skills": row["skills_list"],
    })

# 维度列表，给前端填下拉框用
degree_list = sorted({j["degree"] for j in jobs if j["degree"]})

# 经验段顺序：按常见顺序排一遍，只保留数据里真实存在的
exp_order = [
    "实习/应届", "0-1年", "1-3年", "2-3年", "2-5年",
    "3-5年", "5-10年", "10年以上", "无经验要求",
]
exp_list = [e for e in exp_order if any(j["exp"] == e for j in jobs)]

city_list = sorted({j["city"] for j in jobs if j["city"]})
direction_list = sorted({j["direction"] for j in jobs if j["direction"]})

# 组合统计： (学历, 经验段, 城市, 方向) → 薪资区间
combo_map = defaultdict(list)
for j in jobs:
    key = f'{j["degree"]}|{j["exp"]}|{j["city"]}|{j["direction"]}'
    combo_map[key].append(j["salary"])

combo_stats = {}
for key, vals in combo_map.items():
    arr = np.array(vals, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        continue
    combo_stats[key] = {
        "n_jobs": int(arr.size),
        "min": float(arr.min()),
        "q1": float(np.percentile(arr, 25)),
        "median": float(np.percentile(arr, 50)),
        "q3": float(np.percentile(arr, 75)),
        "max": float(arr.max()),
    }

# 全局技能频率（当作推荐“应该补”的候选池之一）
all_skills = []
for j in jobs:
    all_skills.extend(j["skills"])
skill_counter = Counter(all_skills)
global_skill_top = [
    {"name": name, "value": int(cnt)}
    for name, cnt in skill_counter.most_common(50)
]

result = {
    # 左侧筛选下拉用
    "degree_list": degree_list,
    "exp_list": exp_list,
    "city_list": city_list,
    "direction_list": direction_list,

    # 右侧图表逻辑用
    "jobs": jobs,                 # 原子样本，前端自由筛
    "combo_stats": combo_stats,   # 组合 → 薪资区间，用于 gauge
    "global_skill_top": global_skill_top,  # 全局热门技能
}

# 输出到 static/data/skill_cockpit.json
out_path = "skill_cockpit.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("skill_cockpit.json 已生成:", out_path)
