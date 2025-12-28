import pandas as pd
import math
import json

# 1. 读取数据
df = pd.read_csv("cleaned_data.csv")

# ==============================
# 一、区域分布图用的 JSON：region_summary.json
#    用于：区域环形饼图 / 区域对比条形图
# ==============================

def map_region(city: str) -> str:
    """根据城市名映射到大区"""
    east = {
        "上海","南京","苏州","杭州","宁波","无锡","常州","南通","扬州","镇江",
        "嘉兴","湖州","绍兴","台州","温州",
        "合肥","芜湖","马鞍山","蚌埠","安庆","阜阳",
        "福州","厦门","泉州","莆田","龙岩",
        "济南","青岛","烟台","威海","淄博","潍坊","临沂","济宁","泰安","东营","滨州","德州"
    }
    south = {
        "广州","深圳","东莞","佛山","中山","珠海","惠州","江门","肇庆","汕头","湛江","茂名",
        "南宁","柳州","桂林","北海","玉林",
        "海口","三亚",
        "昆明","曲靖","大理","红河","玉溪"
    }
    north = {
        "北京","天津","石家庄","唐山","保定","秦皇岛","廊坊","邯郸","沧州","承德",
        "太原","大同","长治","晋中","运城"
    }
    northeast = {
        "沈阳","大连","长春","哈尔滨","吉林","鞍山","抚顺","营口","盘锦","本溪","四平"
    }
    central = {
        "武汉","长沙","郑州","南昌","合肥","襄阳","宜昌","洛阳","新乡","信阳","九江","赣州"
    }
    southwest = {
        "成都","重庆","贵阳","昆明","拉萨","绵阳","南充","乐山","泸州","德阳"
    }
    northwest = {
        "西安","兰州","银川","乌鲁木齐","西宁","榆林","咸阳","宝鸡"
    }

    if city in east:
        return "华东"
    if city in south:
        return "华南"
    if city in north:
        return "华北"
    if city in northeast:
        return "东北"
    if city in central:
        return "华中"
    if city in southwest:
        return "西南"
    if city in northwest:
        return "西北"
    return "其他地区"

# 映射大区
df["大区"] = df["工作城市"].apply(map_region)

# 按大区聚合：岗位数量 & 平均中位月薪
region_group = (
    df.groupby("大区")
      .agg(
          job_count=("招聘岗位", "size"),
          avg_salary=("中位月薪_元", "mean")
      )
      .reset_index()
      .sort_values("job_count", ascending=False)
)

region_summary = [
    {
        "name": row["大区"],                        # 大区名称
        "job_count": int(row["job_count"]),        # 岗位数量
        "avg_salary": (
            round(row["avg_salary"], 2)
            if not math.isnan(row["avg_salary"]) else None
        )                                          # 该大区平均中位月薪（可选，用 tooltip 显示）
    }
    for _, row in region_group.iterrows()
]

with open("region_summary.json", "w", encoding="utf-8") as f:
    json.dump(region_summary, f, ensure_ascii=False, indent=2)

print("✅ 已生成 region_summary.json")


# ==============================
# 二、城市 × 月份 多折线图 JSON：city_month_trend.json
#    替代原来的“城市×月份热力图”，更好看也更好讲
# ==============================

# 1）选出岗位数最多的 Top K 城市（避免线太多）
K_CITY = 9
city_counts = (
    df.groupby("工作城市")["招聘岗位"]
      .count()
      .sort_values(ascending=False)
)
top_cities = city_counts.head(K_CITY).index.tolist()

# 2）整理月份（按照字符串排序即可：2024-01, 2024-02, ...）
months = sorted(df["发布月份"].unique().tolist())

# 3）筛选出 Top 城市的数据，做一个 城市 × 月份 的计数表
sub = df[df["工作城市"].isin(top_cities)]
pivot = (
    sub.pivot_table(
        index="工作城市",
        columns="发布月份",
        values="招聘岗位",
        aggfunc="count",
        fill_value=0
    )
    .reindex(index=top_cities, columns=months, fill_value=0)
)

# 4）构造给 ECharts 用的 series 结构：
# {
#   "months": ["2024-01", "2024-02", ...],
#   "series": [
#       {"name": "北京", "data": [22, 27, 410, ...]},
#       {"name": "深圳", "data": [...]},
#       ...
#   ]
# }
series_list = []
for city in top_cities:
    counts = [int(pivot.loc[city, m]) for m in months]
    series_list.append({
        "name": city,
        "data": counts
    })

city_month_trend = {
    "months": months,
    "series": series_list
}

with open("city_month_trend.json", "w", encoding="utf-8") as f:
    json.dump(city_month_trend, f, ensure_ascii=False, indent=2)

print("✅ 已生成 city_month_trend.json")
