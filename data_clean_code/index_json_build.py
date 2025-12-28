import pandas as pd
import json
import re
from pathlib import Path

# === 基本路径设置 ===
csv_path ="cleaned_data.csv"

df = pd.read_csv(csv_path)

# 保证关键字段存在（你这份表里都有）
required_cols = ["发布月份", "主要AI方向", "工作城市", "中位月薪_元", "核心技能列表", "AI标签列表"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"缺少必要字段: {missing}")

# =======================
# ① 多折线趋势图 trend.json
# =======================

# 1）按 AI 方向总量排序，取 Top5 做折线
direction_counts = df["主要AI方向"].value_counts()
top_directions = direction_counts.head(5).index.tolist()

# 2）月份顺序
months = sorted(df["发布月份"].dropna().unique().tolist())

trend_series = []
for direction in top_directions:
    sub = df[df["主要AI方向"] == direction]
    counts_by_month = sub.groupby("发布月份").size()
    # 按 months 顺序补齐，没有的月份用 0
    data = [int(counts_by_month.get(m, 0)) for m in months]
    trend_series.append({
        "name": direction,
        "type": "line",    # 给前端 ECharts 直接用
        "smooth": True,
        "data": data
    })

trend_payload = {
    "months": months,
    "series": trend_series
}

with open("trend.json", "w", encoding="utf-8") as f:
    json.dump(trend_payload, f, ensure_ascii=False, indent=2)

print("已生成 trend.json")


# ============================
# ② 全国岗位 Geo 气泡图 geo.json
# ============================

geo_group = (
    df.groupby("工作城市")
      .agg(jobs=("招聘岗位", "size"), salary=("中位月薪_元", "mean"))
      .reset_index()
)

# 去掉城市名缺失的记录
geo_group = geo_group[geo_group["工作城市"].notna()]

# 按岗位数排序取 Top30
# geo_group = geo_group.sort_values("jobs", ascending=False).head(30)

geo_list = []
for _, row in geo_group.iterrows():
    city = str(row["工作城市"]).strip()
    jobs = int(row["jobs"])
    salary = float(row["salary"]) if pd.notna(row["salary"]) else None
    item = {"name": city, "value": jobs}
    if salary is not None:
        item["salary"] = salary
    geo_list.append(item)

with open( "geo.json", "w", encoding="utf-8") as f:
    json.dump(geo_list, f, ensure_ascii=False, indent=2)

print("已生成 geo.json")


# ====================================
# ③ 岗位类别玫瑰图（AI方向） rose.json
# ====================================

rose_group = (
    df.groupby("主要AI方向")
      .agg(jobs=("招聘岗位", "size"), salary=("中位月薪_元", "mean"))
      .reset_index()
)

rose_group = rose_group[rose_group["主要AI方向"].notna()]
rose_group = rose_group.sort_values("jobs", ascending=False).head(12)

rose_list = []
for _, row in rose_group.iterrows():
    name = str(row["主要AI方向"]).strip()
    jobs = int(row["jobs"])
    salary = float(row["salary"]) if pd.notna(row["salary"]) else None
    item = {"name": name, "value": jobs}
    if salary is not None:
        item["salary"] = salary
    rose_list.append(item)

with open("rose.json", "w", encoding="utf-8") as f:
    json.dump(rose_list, f, ensure_ascii=False, indent=2)

print("已生成 rose.json")


# ============================
# ④ AI 技能词云 wordcloud.json
# ============================

skills_counter = {}

def add_tokens(text):
    if not isinstance(text, str):
        return
    # 用中文顿号、中文逗号、西文逗号、分号、斜杠、空白拆词
    for token in re.split(r"[、，,;/\s]+", text):
        token = token.strip()
        if not token:
            continue
        skills_counter[token] = skills_counter.get(token, 0) + 1

for col in ["核心技能列表", "AI标签列表"]:
    df[col].fillna("").apply(add_tokens)

# 词频排序，取 Top100
sorted_skills = sorted(skills_counter.items(), key=lambda x: x[1], reverse=True)[:100]

wc_list = [{"name": name, "value": int(count)} for name, count in sorted_skills]

with open( "wordcloud.json", "w", encoding="utf-8") as f:
    json.dump(wc_list, f, ensure_ascii=False, indent=2)

print("已生成 wordcloud.json")
