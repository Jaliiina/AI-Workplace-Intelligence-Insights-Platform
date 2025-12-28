import pandas as pd
import json
import math
import re
from collections import Counter, defaultdict

# =========================
# 0. 读取数据 & 基本设置
# =========================
CSV_FILE = "cleaned_data.csv"

# 把“岗位类别”统一理解为：主要 AI 方向
CAT_COL = "主要AI方向"

df = pd.read_csv(CSV_FILE)

# 去掉类别为空的行
df = df.dropna(subset=[CAT_COL]).copy()

# =========================
# 1. 按类别聚合基础统计
# =========================
cat_group = (
    df.groupby(CAT_COL)
      .agg(
          job_count=("招聘岗位", "size"),       # 岗位数量
          avg_salary=("中位月薪_元", "mean"),  # 平均中位月薪
          city_count=("工作城市", "nunique"),   # 覆盖城市数
          month_count=("发布月份", "nunique")   # 有岗位的月份数
      )
      .reset_index()
      .sort_values("job_count", ascending=False)
)

# 防止种类太多，统一只取前 K 个类别
TOP_K_CATEGORY = 10
cat_top = cat_group.head(TOP_K_CATEGORY).reset_index(drop=True)

# =========================
# ⑨ 岗位类别占比玫瑰图
# 文件：job_category_rose.json
# 结构：[{"name": 类别, "value": 岗位数, "avg_salary": 平均薪资}, ...]
# =========================
rose_data = [
    {
        "name": row[CAT_COL],
        "value": int(row["job_count"]),
        "avg_salary": (
            round(row["avg_salary"], 2)
            if not math.isnan(row["avg_salary"]) else None
        )
    }
    for _, row in cat_top.iterrows()
]

with open("job_category_rose.json", "w", encoding="utf-8") as f:
    json.dump(rose_data, f, ensure_ascii=False, indent=2)

print("✅ ⑨ job_category_rose.json 生成完毕")


# =========================
# ⑩ 类别平均薪资对比 Grouped Bar
# 文件：job_category_compare.json
# 结构：
# {
#   "categories": [...],
#   "job_count": [...],
#   "avg_salary": [...]
# }
# =========================
compare_json = {
    "categories": cat_top[CAT_COL].tolist(),
    "job_count": [int(x) for x in cat_top["job_count"]],
    "avg_salary": [
        round(x, 2) if not math.isnan(x) else None
        for x in cat_top["avg_salary"]
    ]
}

with open("job_category_compare.json", "w", encoding="utf-8") as f:
    json.dump(compare_json, f, ensure_ascii=False, indent=2)

print("✅ ⑩ job_category_compare.json 生成完毕")


# =========================
# ⑪ 类别词云（按岗位类别过滤）
# 文件：category_wordcloud.json
#
# 使用列：核心技能列表
# 每个类别一个词云：
# [
#   {
#     "category": "人工智能",
#     "words": [
#       {"name": "Python", "value": 120},
#       {"name": "深度学习", "value": 80},
#       ...
#     ]
#   },
#   ...
# ]
# =========================
SKILL_COL = "核心技能列表"

if SKILL_COL in df.columns:
    df_top_cat = df[df[CAT_COL].isin(cat_top[CAT_COL])].copy()

    # 分词：用 中文顿号、中文逗号、英文逗号、分号、竖线、空格 作为分隔
    pattern = re.compile(r"[、，,;；\|\s]+")

    cat_word_counter: dict[str, Counter] = defaultdict(Counter)

    for _, row in df_top_cat.iterrows():
        text = str(row.get(SKILL_COL, "")).strip()
        if not text or text.lower() == "nan":
            continue
        words = [w for w in pattern.split(text) if w]
        cat = row[CAT_COL]
        cat_word_counter[cat].update(words)

    category_wordcloud = []
    TOP_WORDS = 80  # 每个类别词云最多展示多少个词

    for _, row in cat_top.iterrows():
        cat = row[CAT_COL]
        counter = cat_word_counter.get(cat, Counter())
        items = counter.most_common(TOP_WORDS)
        if not items:
            continue

        data_words = [
            {"name": w, "value": int(c)}
            for w, c in items
        ]
        category_wordcloud.append({
            "category": cat,
            "words": data_words
        })

    with open("category_wordcloud.json", "w", encoding="utf-8") as f:
        json.dump(category_wordcloud, f, ensure_ascii=False, indent=2)

    print("✅ ⑪ category_wordcloud.json 生成完毕")
else:
    print("⚠️ 未找到技能列：核心技能列表，请确认列名")


# =========================
# ⑫ 岗位能力雷达图（Radar）
# 文件：job_category_radar.json
#
# 维度设计：
# - 岗位数量
# - 平均薪资
# - 城市覆盖数
# - 活跃月份数
#
# 结构：
# {
#   "indicators": [
#     {"name": "岗位数量", "max": ...},
#     {"name": "平均薪资", "max": ...},
#     {"name": "城市覆盖数", "max": ...},
#     {"name": "活跃月份数", "max": ...}
#   ],
#   "series": [
#     {"name": "人工智能", "value": [job_count, avg_salary, city_cnt, month_cnt]},
#     ...
#   ]
# }
# =========================

def with_margin(x, ratio=1.1):
    return int(math.ceil(x * ratio)) if x > 0 else 1

max_job_count = int(cat_top["job_count"].max()) if len(cat_top) > 0 else 0
max_avg_salary = float(cat_top["avg_salary"].max()) if len(cat_top) > 0 else 0.0
max_city_count = int(cat_top["city_count"].max()) if len(cat_top) > 0 else 0
max_month_count = int(cat_top["month_count"].max()) if len(cat_top) > 0 else 0

indicators = [
    {"name": "岗位数量", "max": with_margin(max_job_count)},
    {"name": "平均薪资", "max": with_margin(max_avg_salary)},
    {"name": "城市覆盖数", "max": with_margin(max_city_count)},
    {"name": "活跃月份数", "max": with_margin(max_month_count)},
]

series_radar = []
for _, row in cat_top.iterrows():
    vals = [
        int(row["job_count"]),
        float(row["avg_salary"]) if not math.isnan(row["avg_salary"]) else 0.0,
        int(row["city_count"]),
        int(row["month_count"]),
    ]
    series_radar.append({
        "name": row[CAT_COL],
        "value": vals
    })

radar_json = {
    "indicators": indicators,
    "series": series_radar
}

with open("job_category_radar.json", "w", encoding="utf-8") as f:
    json.dump(radar_json, f, ensure_ascii=False, indent=2)

print("✅ ⑫ job_category_radar.json 生成完毕")
