# prepare_skill_cockpit.py
import pandas as pd
import numpy as np
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
csv_path = BASE_DIR / "cleaned_data.csv"

df = pd.read_csv(csv_path)

required_cols = ["工作城市", "主要AI方向", "学历层级", "经验段", "中位月薪_元", "核心技能列表"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise SystemExit(f"缺少必要字段: {missing}")

def split_skills(text: str):
    if not isinstance(text, str):
        return []
    parts = re.split(r"[、，,;/\s]+", text)
    return [p.strip() for p in parts if p.strip()]

df["skills_list"] = df["核心技能列表"].apply(split_skills)

jobs = []
for idx, row in df.iterrows():
    salary = row["中位月薪_元"]
    if pd.isna(salary):
        continue

    jobs.append({
        "id": int(idx),
        "city": None if pd.isna(row["工作城市"]) else str(row["工作城市"]),
        "direction": None if pd.isna(row["主要AI方向"]) else str(row["主要AI方向"]),
        "degree": None if pd.isna(row["学历层级"]) else str(row["学历层级"]),
        "exp": None if pd.isna(row["经验段"]) else str(row["经验段"]),
        "salary": float(salary),
        "skills": row["skills_list"],
    })

degree_list = sorted({j["degree"] for j in jobs if j["degree"]})

exp_order = [
    "实习/应届", "0-1年", "1-3年", "2-3年", "2-5年",
    "3-5年", "5-10年", "10年以上", "无经验要求",
]
exp_list = [e for e in exp_order if any(j["exp"] == e for j in jobs)]

city_list = sorted({j["city"] for j in jobs if j["city"]})
direction_list = sorted({j["direction"] for j in jobs if j["direction"]})

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

all_skills = []
for j in jobs:
    all_skills.extend(j["skills"])
skill_counter = Counter(all_skills)
global_skill_top = [
    {"name": name, "value": int(cnt)}
    for name, cnt in skill_counter.most_common(50)
]

result = {
    "degree_list": degree_list,
    "exp_list": exp_list,
    "city_list": city_list,
    "direction_list": direction_list,
    "jobs": jobs,
    "combo_stats": combo_stats,
    "global_skill_top": global_skill_top,
}

out_path ="skill_cockpit.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("skill_cockpit.json 已生成:", out_path)
