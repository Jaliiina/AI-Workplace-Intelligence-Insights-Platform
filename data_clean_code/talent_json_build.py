import pandas as pd
import numpy as np
import json

# 1. 读源数据
df = pd.read_csv("cleaned_data.csv")

# 只保留有薪资和学历的数据，避免 NaN 干扰
df = df.copy()
df["中位月薪_元"] = pd.to_numeric(df["中位月薪_元"], errors="coerce")
salary_col = "中位月薪_元"
degree_col = "学历层级"
exp_col = "经验段"

# =========================
# ⑬ / ⑯ 学历占比（玫瑰图 + 漏斗图）→ degree_counts.json
# =========================
degree_counts = (
    df[degree_col]
    .dropna()
    .value_counts()
    .reset_index()
)
degree_counts.columns = ["degree", "count"]

# 按数量排序（方便漏斗图从大到小）
degree_counts = degree_counts.sort_values("count", ascending=False)

degree_counts_data = [
    {"name": str(row["degree"]), "value": int(row["count"])}
    for _, row in degree_counts.iterrows()
]

degree_counts_json = {
    # 类目
    "degrees": degree_counts["degree"].astype(str).tolist(),
    # 计数
    "counts": degree_counts["count"].astype(int).tolist(),
    # 直接给 ECharts 用的 [{name, value}]，玫瑰图 / 漏斗图都能用
    "data": degree_counts_data
}

with open("degree_counts.json", "w", encoding="utf-8") as f:
    json.dump(degree_counts_json, f, ensure_ascii=False, indent=2)

print("Saved: degree_counts.json")

# =========================
# ⑭ 学历 × 薪资 Bar → degree_salary.json
# =========================
degree_salary = (
    df[[degree_col, salary_col]]
    .dropna()
    .groupby(degree_col)[salary_col]
    .agg(["count", "mean", "median", "min", "max"])
    .reset_index()
)

# 用中位数排序，更稳一点
degree_salary = degree_salary.sort_values("median")

degree_salary_json = {
    "degrees": degree_salary[degree_col].astype(str).tolist(),
    # 这里给一堆指标，你前端可以挑自己要画的
    "count": degree_salary["count"].astype(int).tolist(),
    "mean": degree_salary["mean"].round(2).tolist(),
    "median": degree_salary["median"].round(2).tolist(),  # 推荐 Bar 用这个
    "min": degree_salary["min"].round(2).tolist(),
    "max": degree_salary["max"].round(2).tolist()
}

with open("degree_salary.json", "w", encoding="utf-8") as f:
    json.dump(degree_salary_json, f, ensure_ascii=False, indent=2)

print("Saved: degree_salary.json")

# =========================
# ⑮ 薪资区间分布直方图 → salary_bins.json
# =========================
# 自定义薪资区间（可以按你需求改）
bins = [0, 5000, 10000, 15000, 20000, 30000, 50000, np.inf]
labels = ["0-5k", "5k-10k", "10k-15k", "15k-20k", "20k-30k", "30k-50k", "50k+"]

salary_notna = df[salary_col].dropna()

salary_bin = pd.cut(
    salary_notna,
    bins=bins,
    labels=labels,
    right=False,         # 左闭右开 [ )
    include_lowest=True  # 包含最左端
)

bin_counts = salary_bin.value_counts().reindex(labels, fill_value=0)

salary_bins_json = {
    "bins": labels,                          # x 轴类目
    "counts": bin_counts.astype(int).tolist(),  # 每个区间数量
    "bin_edges": [float(b) if np.isfinite(b) else "inf" for b in bins]  # 可选
}

with open("salary_bins.json", "w", encoding="utf-8") as f:
    json.dump(salary_bins_json, f, ensure_ascii=False, indent=2)

print("Saved: salary_bins.json")

# =========================
# ⑰ 经验 × 薪资箱线图（Boxplot） → experience_salary_boxplot.json
# =========================
def five_number(series: pd.Series):
    """返回 [min, Q1, median, Q3, max]"""
    x = series.dropna().to_numpy()
    if x.size == 0:
        return [None] * 5
    return [
        float(np.min(x)),
        float(np.percentile(x, 25)),
        float(np.percentile(x, 50)),
        float(np.percentile(x, 75)),
        float(np.max(x))
    ]

box_categories = []
box_data = []

# 可以先按经验段排序（简单按字符串排一下）
for exp, group in df[[exp_col, salary_col]].dropna().groupby(exp_col):
    box_categories.append(str(exp))
    box_data.append(five_number(group[salary_col]))

experience_salary_boxplot_json = {
    # ECharts boxplot 的 x 轴类目
    "categories": box_categories,
    # 对应每个经验段的 [min, Q1, median, Q3, max]
    "boxData": box_data,
    # 如果你想做离群点，可以再单独算，这里先不给，
    # 前端完全可以忽略 outliers 只画基本箱线
    "outliers": []
}

with open("experience_salary_boxplot.json", "w", encoding="utf-8") as f:
    json.dump(experience_salary_boxplot_json, f, ensure_ascii=False, indent=2)

print("Saved: experience_salary_boxplot.json")
