# prepare_skill_drill.py
import pandas as pd
import numpy as np
import re
import json
from collections import Counter

# 1. 读原始清洗好的数据
df = pd.read_csv("cleaned_data.csv")

# 经验段顺序（按你数据里实际有的来排）
EXPERIENCE_ORDER = [
    "实习/应届",
    "0-1年",
    "1-3年",
    "2-3年",
    "2-5年",
    "3-5年",
    "5-10年",
    "10年以上",
    "无经验要求",
]

def split_skills(text: str):
    """把“核心技能列表”拆成单个技能"""
    if not isinstance(text, str):
        return []
    parts = re.split(r"[、，,;/\s]+", text)
    return [p.strip() for p in parts if p.strip()]

# 2. 统计所有技能频次，挑 Top N 做下拉
all_skills = []
for s in df["核心技能列表"].dropna():
    all_skills.extend(split_skills(s))

skill_counter = Counter(all_skills)
TOP_N = 50   # 你可以改成 30/80 等

def build_single_skill_data(skill_name: str, df: pd.DataFrame):
    """针对某个 skill 聚合出：薪资箱线、经验-薪资曲线、城市分布、方向分布"""
    # 在“核心技能列表”中包含这个技能的行
    sub = df[df["核心技能列表"].astype(str).str.contains(re.escape(skill_name))]
    if sub.empty:
        return None

    # 1) 薪资箱线图数据
    salary_series = sub["中位月薪_元"].dropna()
    if not salary_series.empty:
        salary_sorted = sorted(salary_series.tolist())
        q1, med, q3 = np.percentile(salary_sorted, [25, 50, 75])
        salary_box = [
            float(min(salary_sorted)),  # min
            float(q1),                  # Q1
            float(med),                 # median
            float(q3),                  # Q3
            float(max(salary_sorted)),  # max
        ]
    else:
        salary_box = None

    # 2) 按经验段的平均薪资曲线
    exp_salary = {}
    for exp in EXPERIENCE_ORDER:
        tmp = sub[sub["经验段"] == exp]
        tmp = tmp["中位月薪_元"].dropna()
        if not tmp.empty:
            exp_salary[exp] = float(round(tmp.mean(), 2))

    # 3) 城市需求 Top10
    city_counts = (
        sub["工作城市"].dropna().value_counts().head(10)
    )
    city_list = [
        {"name": city, "value": int(cnt)}
        for city, cnt in city_counts.items()
    ]

    # 4) 主要 AI 方向分布 Top8
    dir_counts = (
        sub["主要AI方向"].dropna().value_counts().head(8)
    )
    direction_list = [
        {"name": d, "value": int(cnt)}
        for d, cnt in dir_counts.items()
    ]

    return {
        "total_jobs": int(sub.shape[0]),
        "salary_box": salary_box,
        "salary_sample_size": int(salary_series.shape[0]),
        "exp_salary": exp_salary,          # dict: {经验段: 平均薪资}
        "city_counts": city_list,          # [{name, value}]
        "direction_counts": direction_list # [{name, value}]
    }

skill_data = {}
for skill, _cnt in skill_counter.most_common(TOP_N):
    info = build_single_skill_data(skill, df)
    if not info:
        continue
    # 简单过滤一下样本太少的技能
    if info["total_jobs"] < 10:
        continue
    skill_data[skill] = info

result = {
    "skills": list(skill_data.keys()),
    "experience_order": EXPERIENCE_ORDER,
    "skill_data": skill_data,
}

# 3. 写出到 static/data/skill_drill.json
#    这里路径看你项目结构，一般是 app.py 同级的 static/data
out_path = "skill_drill.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"生成完成，共 {len(skill_data)} 个技能，已保存到 {out_path}")
