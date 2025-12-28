# prepare_skill_drill.py
import pandas as pd
import numpy as np
import re
import json
from collections import Counter
from pathlib import Path

# ========== 0. 路径 & 读原始数据 ==========
BASE_DIR = Path(__file__).resolve().parent
csv_path = BASE_DIR / "cleaned_data.csv"

df = pd.read_csv(csv_path)

# 这里假设字段名如下，和你之前保持一致：
# 工作城市 / 中位月薪_元 / 经验段 / 主要AI方向 / 核心技能列表
REQUIRED_COLS = ["工作城市", "中位月薪_元", "经验段", "主要AI方向", "核心技能列表"]
for c in REQUIRED_COLS:
    if c not in df.columns:
        raise ValueError(f"缺少必要字段：{c}")

# 经验段的排序（按你数据实际情况可以改）
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

# ========== 1. 工具函数：拆技能 ==========
def split_skills(text: str):
    """把“核心技能列表”拆成单个技能字符串列表"""
    if not isinstance(text, str):
        return []
    parts = re.split(r"[、，,;/\s]+", text)
    return [p.strip() for p in parts if p.strip()]


# ========== 2. 统计所有技能词频，选 Top N 做下拉 ==========
all_skills = []
for s in df["核心技能列表"].dropna():
    all_skills.extend(split_skills(s))

skill_counter = Counter(all_skills)
TOP_N = 50  # 你想展示多少个技能就改这里

# ========== 3. 定义薪资直方图分箱 ==========
# 先看全局薪资范围，估个合理区间
salary_all = df["中位月薪_元"].dropna()
if salary_all.empty:
    raise ValueError("中位月薪_元 列没有有效数据")

global_min = salary_all.min()
global_max = salary_all.max()

# 粗暴但好理解：从 0 到 60k 左右分箱（单位：元）
# 你可以按需求改，比如 5k 一档
bins = [0, 5000, 10000, 15000, 20000, 30000, 40000, 60000, 100000]
bin_labels = ["0-5k", "5-10k", "10-15k", "15-20k", "20-30k", "30-40k", "40-60k", "60k+"]

# ========== 4. 经验段雷达图的全局最大值 ==========
exp_salary_global = []
for exp in EXPERIENCE_ORDER:
    tmp = df[df["经验段"] == exp]["中位月薪_元"].dropna()
    if not tmp.empty:
        exp_salary_global.append(tmp.mean())

if exp_salary_global:
    radar_max = float(max(exp_salary_global) * 1.1)  # 稍微放大一点做上限
else:
    radar_max = 50000.0

# ========== 5. 针对单个技能构建聚合数据 ==========
def build_single_skill_data(skill_name: str, df: pd.DataFrame):
    """
    针对某个 skill 聚合出：
    - 薪资直方图 bins
    - 经验段雷达数据
    - 城市需求 Top10
    - AI 方向分布
    """
    mask = df["核心技能列表"].astype(str).str.contains(re.escape(skill_name))
    sub = df[mask]
    if sub.empty:
        return None

    # 1) 薪资直方图
    salary_series = sub["中位月薪_元"].dropna()
    if not salary_series.empty:
        cut = pd.cut(salary_series, bins=bins, labels=bin_labels, right=False, include_lowest=True)
        hist_counts = cut.value_counts().sort_index()
        salary_hist = [
            {"bin": label, "value": int(hist_counts.get(label, 0))}
            for label in bin_labels
        ]
    else:
        salary_hist = []

    # 2) 经验段平均薪资（雷达图用）
    exp_salary = {}
    for exp in EXPERIENCE_ORDER:
        tmp = sub[sub["经验段"] == exp]["中位月薪_元"].dropna()
        if not tmp.empty:
            exp_salary[exp] = float(round(tmp.mean(), 2))

    # 3) 城市需求 Top10（极坐标玫瑰图）
    city_counts = sub["工作城市"].dropna().value_counts().head(10)
    city_list = [
        {"name": city, "value": int(cnt)}
        for city, cnt in city_counts.items()
    ]

    # 4) 主要 AI 方向分布（Sunburst）
    dir_counts = sub["主要AI方向"].dropna().value_counts()
    direction_list = [
        {"name": d, "value": int(cnt)}
        for d, cnt in dir_counts.items()
    ]

    return {
        "total_jobs": int(sub.shape[0]),
        "salary_hist": salary_hist,          # [{bin, value}]
        "salary_sample_size": int(salary_series.shape[0]),
        "exp_salary": exp_salary,            # {经验段: 平均薪资}
        "city_counts": city_list,            # [{name, value}]
        "direction_counts": direction_list   # [{name, value}]
    }


skill_data = {}
for skill, _cnt in skill_counter.most_common(TOP_N):
    info = build_single_skill_data(skill, df)
    if not info:
        continue
    # 太冷门直接过滤掉
    if info["total_jobs"] < 10:
        continue
    skill_data[skill] = info

result = {
    "skills": list(skill_data.keys()),            # 下拉候选
    "experience_order": EXPERIENCE_ORDER,         # 雷达维度顺序
    "salary_bins": bin_labels,                    # 直方图分箱标签
    "radar_max": radar_max,                       # 雷达图纵轴上限
    "skill_data": skill_data                      # 每个技能的具体数据
}

# ========== 6. 写出 JSON ==========
out_dir = BASE_DIR / "static" / "data"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "skill_drill.json"

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"生成完成：{len(skill_data)} 个技能")
print(f"已保存到：{out_path}")
