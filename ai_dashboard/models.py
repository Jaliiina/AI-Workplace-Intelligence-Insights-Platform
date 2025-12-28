# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(64))
    direction = db.Column(db.String(128))
    degree = db.Column(db.String(32))
    exp = db.Column(db.String(32))
    median_salary = db.Column(db.Float)
    source_index = db.Column(db.Integer)  # 对应 cleaned_data.csv 的行号


class JobSkill(db.Model):
    __tablename__ = "job_skills"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"))
    skill = db.Column(db.String(128))


class UserQuery(db.Model):
    __tablename__ = "user_queries"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64))
    degree = db.Column(db.String(32))
    exp = db.Column(db.String(32))
    city = db.Column(db.String(64))
    direction = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, server_default=db.func.now())
