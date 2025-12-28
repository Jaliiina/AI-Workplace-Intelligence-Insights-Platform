import pandas as pd
import re
from app import app  # 注意：这里是从你的 app.py 导入 app
from models import db, Job, JobSkill

def split_skills(text):
    if not isinstance(text, str):
        return []
    parts = re.split(r"[、，,;/\s]+", text)
    return [p.strip() for p in parts if p.strip()]

def run():
    df = pd.read_csv("cleaned_data.csv")

    required_cols = ["工作城市", "主要AI方向", "学历层级", "经验段", "中位月薪_元", "核心技能列表"]
    for c in required_cols:
        if c not in df.columns:
            raise SystemExit(f"缺少字段：{c}")

    with app.app_context():
        # 开发阶段：每次导入前先清空
        JobSkill.query.delete()
        Job.query.delete()
        db.session.commit()

        for idx, row in df.iterrows():
            job = Job(
                city=row["工作城市"],
                direction=row["主要AI方向"],
                degree=row["学历层级"],
                exp=row["经验段"],
                median_salary=row["中位月薪_元"] if not pd.isna(row["中位月薪_元"]) else None,
                source_index=int(idx),
            )
            db.session.add(job)
            db.session.flush()  # 拿到 job.id

            skills = split_skills(row["核心技能列表"])
            for s in skills:
                db.session.add(JobSkill(job_id=job.id, skill=s))

        db.session.commit()
        print("导入完成，共写入 Job 行数：", Job.query.count())

if __name__ == "__main__":
    run()
