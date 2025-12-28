import pandas as pd
import json
import requests
import time
import csv
from pathlib import Path
from datetime import datetime

# ========= 配置 =========
RAW_PATH = "/home/user/jdy/hw2/人工智能招聘大数据2024年.xlsx"

# 输出文件名
OUT_CSV = "/home/user/jdy/clean_ai_jobs_ollama.csv"


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen3:32b"

SLEEP_SEC = 0.5  # 每条之间停一下，别把机器榨干


# ========= Prompt =========

SYSTEM_PROMPT = """你是一个招聘数据清洗助手，负责将原始招聘信息规范成结构化 JSON。
不要发挥想象，只根据给定内容进行合理推断。
所有数字统一用阿拉伯数字，JSON 必须能被严格解析。"""

USER_INSTRUCTION = """
下面是一条人工智能相关岗位的招聘数据，请你根据原始字段，输出一个结构化 JSON。

【原始数据】
- 招聘岗位：{job_title}
- 企业名称：{company_name}
- 工作城市：{city}
- 工作区域：{area}
- 最低月薪：{salary_min_raw}
- 最高月薪：{salary_max_raw}
- 要求经验：{exp_raw}
- 学历要求：{degree_raw}
- 人工智能关键词：{ai_keywords_raw}
- 职位描述：{job_desc}

【字段标准化要求】

请你只返回一个 JSON 对象，字段必须是下面这些（字段名用中文，不能多也不能少）：

- "招聘岗位": 标准化后的岗位名称（中文字符串）
- "企业名称": 企业名称（字符串）
- "工作城市": 工作城市（尽量简化成市级，例如“北京市”统一为“北京”）
- "工作区域": 工作区域（可以保留原文，去掉明显噪音即可）

- "最低月薪_元": 最低月薪，整数，单位为“元/月”，无法确定时用 null
- "最高月薪_元": 最高月薪，整数，单位为“元/月”，无法确定时用 null

- "经验段": 经验区间，取值只能是以下之一：
  ["实习/应届","0-1年","1-3年","3-5年","5-10年","10年以上","无经验要求"]
  说明：
    - 在校生/应届生/实习 → "实习/应届"
    - 无需经验 / 不限经验 → "无经验要求"
    - 像“1-3年”“1年及以上”“1-3 年经验”统一归到最接近的区间

- "经验年限下限": 最低年限（整数），无法确定用 null
- "经验年限上限": 最高年限（整数），无法确定用 null

- "学历层级": 学历标准枚举，取值只能是：
  ["博士","硕士","本科","大专","中专及以下","不限"]
  对应关系示例：
    - 博士 → "博士"
    - 研究生/硕士 → "硕士"
    - 本科/学士 → "本科"
    - 大专 → "大专"
    - 中技/中专/职高 → "中专及以下"
    - 学历不限/无要求 → "不限"

- "AI标签列表": 从“人工智能关键词”字段中拆分得到的列表（按中文逗号、顿号、空格分割），去重后返回，
   例如 ["机器学习","深度学习","数据挖掘"]。
   优先使用该字段，若为空，可从职位描述中提取 1-5 个核心 AI 方向。

- "主要AI方向": 在 "AI标签列表" 中选一个最能代表该岗位方向的标签
   （例如“机器学习”“深度学习”“大数据处理”“机器人自动化”“无人驾驶”“人工智能”），
   如果没有合适的就用 "人工智能"。

- "岗位摘要": 用中文 20 个字左右概括岗位核心工作内容。

- "核心技能列表": 从职位描述中提取 3-8 个关键技能词（中文数组），
   例如 ["Python","机器学习","数据挖掘"]。

【必须严格遵守】
1. 只能返回 JSON 对象本身，不要任何多余说明。
2. JSON 必须是合法的、可被 json.loads 解析。
3. 所有字段名必须完全等于上面给出的中文名称。
"""


# ========= 调用 ollama =========

def call_ollama(row_dict, retry=3):
    user_prompt = USER_INSTRUCTION.format(
        job_title=row_dict.get("招聘岗位", "") or "",
        company_name=row_dict.get("企业名称", "") or "",
        city=row_dict.get("工作城市", "") or "",
        area=row_dict.get("工作区域", "") or "",
        salary_min_raw=row_dict.get("最低月薪", "") or "",
        salary_max_raw=row_dict.get("最高月薪", "") or "",
        exp_raw=row_dict.get("要求经验", "") or "",
        degree_raw=row_dict.get("学历要求", "") or "",
        ai_keywords_raw=row_dict.get("人工智能关键词", "") or "",
        job_desc=row_dict.get("职位描述", "") or "",
    )

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }

    for attempt in range(retry):
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=600)
            resp.raise_for_status()
            data = resp.json()
            content = data["message"]["content"]

            text = content.strip()
            if text.startswith("```"):
                parts = text.split("```")
                if len(parts) >= 3:
                    text = parts[1]
                text = text.strip()
                if text.lower().startswith("json"):
                    text = text[4:].strip()

            try:
                obj = json.loads(text)
            except json.JSONDecodeError:
                text2 = text.replace("'", '"')
                obj = json.loads(text2)

            return obj

        except Exception as e:
            print(f"[warn] 调用 ollama 失败，第 {attempt+1} 次重试：{e}")
            time.sleep(1.5)

    raise RuntimeError("调用 ollama 多次失败，放弃这一行。")


def make_fallback(row_dict):
    """模型彻底挂了时的兜底结构，避免整表断掉。"""
    return {
        "招聘岗位": row_dict.get("招聘岗位", "") or "",
        "企业名称": row_dict.get("企业名称", "") or "",
        "工作城市": row_dict.get("工作城市", "") or "",
        "工作区域": row_dict.get("工作区域", "") or "",
        "最低月薪_元": None,
        "最高月薪_元": None,
        "经验段": "无经验要求",
        "经验年限下限": None,
        "经验年限上限": None,
        "学历层级": "不限",
        "AI标签列表": [],
        "主要AI方向": "人工智能",
        "岗位摘要": "",
        "核心技能列表": []
    }


# ========= 主流程：一条处理一条写 =========

def main():
    raw_path = Path(RAW_PATH)
    if not raw_path.exists():
        raise FileNotFoundError(f"未找到原始文件：{raw_path.absolute()}")

    print(f"读取原始数据：{raw_path}")
    df_raw = pd.read_excel(raw_path)

    needed_cols = [
        "招聘岗位", "企业名称", "工作城市", "工作区域",
        "最低月薪", "最高月薪",
        "要求经验", "学历要求",
        "人工智能关键词", "职位描述",
        "招聘发布日期"
    ]
    for col in needed_cols:
        if col not in df_raw.columns:
            print(f"[warn] 原始表中缺少列：{col}，这一列将为空。")

    total = len(df_raw)
    print(f"共 {total} 条记录，开始逐行处理（每条写入一次）。")

    # 输出字段顺序（中文字段）
    fieldnames = [
        "招聘岗位", "企业名称", "工作城市", "工作区域",
        "最低月薪_元", "最高月薪_元", "中位月薪_元",
        "经验段", "经验年限下限", "经验年限上限",
        "学历层级", "AI标签列表", "主要AI方向",
        "岗位摘要", "核心技能列表",
        "招聘发布日期", "发布月份"
    ]

    out_path = Path(OUT_CSV)
    header_written = out_path.exists() and out_path.stat().st_size > 0

    # 一次打开文件，循环写入每一行
    with open(out_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not header_written:
            writer.writeheader()

        for idx, row in df_raw.iterrows():
            row_dict = row.to_dict()
            print(f"\n[{idx+1}/{total}] 处理：{row_dict.get('招聘岗位','')} @ {row_dict.get('工作城市','')}")

            try:
                clean_obj = call_ollama(row_dict)
            except Exception as e:
                print(f"[error] 模型调用失败，使用兜底结构：{e}")
                clean_obj = make_fallback(row_dict)

            # 计算中位月薪
            try:
                smin = clean_obj.get("最低月薪_元")
                smax = clean_obj.get("最高月薪_元")
                if smin is None or smax is None:
                    mid = None
                else:
                    mid = (float(smin) + float(smax)) / 2.0
            except Exception:
                mid = None

            # 招聘发布日期 & 发布月份
            pub_raw = row_dict.get("招聘发布日期", "")
            pub_str = ""
            month_str = ""
            if pd.notna(pub_raw):
                pub_str = str(pub_raw)
                try:
                    dt = pd.to_datetime(pub_raw)
                    month_str = dt.to_period("M").strftime("%Y-%m")
                except Exception:
                    month_str = ""

            # 把列表字段转成字符串（方便 CSV 查看）
            ai_tags = clean_obj.get("AI标签列表", [])
            if isinstance(ai_tags, list):
                ai_tags_str = "、".join(str(x) for x in ai_tags)
            else:
                ai_tags_str = str(ai_tags)

            skills = clean_obj.get("核心技能列表", [])
            if isinstance(skills, list):
                skills_str = "、".join(str(x) for x in skills)
            else:
                skills_str = str(skills)

            row_out = {
                "招聘岗位": clean_obj.get("招聘岗位", ""),
                "企业名称": clean_obj.get("企业名称", ""),
                "工作城市": clean_obj.get("工作城市", ""),
                "工作区域": clean_obj.get("工作区域", ""),
                "最低月薪_元": clean_obj.get("最低月薪_元", None),
                "最高月薪_元": clean_obj.get("最高月薪_元", None),
                "中位月薪_元": mid,
                "经验段": clean_obj.get("经验段", ""),
                "经验年限下限": clean_obj.get("经验年限下限", None),
                "经验年限上限": clean_obj.get("经验年限上限", None),
                "学历层级": clean_obj.get("学历层级", ""),
                "AI标签列表": ai_tags_str,
                "主要AI方向": clean_obj.get("主要AI方向", ""),
                "岗位摘要": clean_obj.get("岗位摘要", ""),
                "核心技能列表": skills_str,
                "招聘发布日期": pub_str,
                "发布月份": month_str,
            }

            writer.writerow(row_out)
            f.flush()
            time.sleep(SLEEP_SEC)

    print(f"\n全部处理完成，结果已写入：{OUT_CSV}")
    print("这个 CSV 直接用 Excel 打开就是中文字段的干净表。")


if __name__ == "__main__":
    main()
