import os
import json
from flask import Flask, render_template, jsonify, current_app, Response, stream_with_context,request
from openai import OpenAI  # 记得先 pip install openai
from flask import request, session, jsonify
from models import db, UserQuery
from sqlalchemy import func 

app = Flask(__name__)

app = Flask(__name__)

# 为了 session_id 能用，随便设一个 secret_key
app.config["SECRET_KEY"] = "123456"  # 可以自定义

# SQLite 数据库配置（文件名 jobs.db）
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///jobs.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# 第一次跑可以自动建表
with app.app_context():
    db.create_all()

# ====== DeepSeek 配置 ======
# 在系统环境变量里配置：DEEPSEEK_API_KEY=你的key
deepseek_client = OpenAI(
    api_key="",
    base_url="https://api.deepseek.com"
)

DEEPSEEK_MODEL = "deepseek-chat"


def load_json_from_static(relative_path: str):
    """
    从 static/data 下读取 json 文件的小工具函数
    比如 relative_path='trend.json' -> static/data/trend.json
    """
    base = os.path.join(current_app.static_folder, "data")
    full = os.path.join(base, relative_path)
    with open(full, "r", encoding="utf-8") as f:
        return json.load(f)


# ========= 页面路由 =========

@app.route('/')
def entry():
    return render_template('entry.html')

@app.route('/structure')
def structure():
    return render_template('structure.html')

@app.route('/city_region')
def city_region():
    return render_template('city_region.html')

@app.route('/main_dashboard')
def main_dashboard():
    return render_template('main_dashboard.html')

@app.route('/skill_talent')
def skill_talent():
    return render_template('skill_talent.html')

@app.route("/chat")
def chat_page():
    return render_template("chat.html")

@app.route("/city_detail")
def city_detail():
    return render_template("city_detail.html")

@app.route("/skill_drill")
def skill_drill():
    return render_template("skill_drill.html")

@app.route("/skill_cockpit")
def skill_cockpit():
    return render_template("skill_cockpit.html")

@app.route("/api/skill_cockpit_log", methods=["POST"])
def skill_cockpit_log():
    data = request.get_json() or {}

    degree = data.get("degree")
    exp = data.get("exp")
    city = data.get("city")
    direction = data.get("direction")

    # 简单搞一个 session_id：没登录就用 ip 代替
    sid = session.get("sid")
    if not sid:
        sid = request.remote_addr or "anon"
        session["sid"] = sid

    uq = UserQuery(
        session_id=sid,
        degree=degree,
        exp=exp,
        city=city,
        direction=direction,
    )
    db.session.add(uq)
    db.session.commit()

    return jsonify({"status": "ok"})

@app.route("/query_insight")
def query_insight():
    # 总条数
    total = db.session.query(func.count(UserQuery.id)).scalar() or 0

    # 最近 20 条
    recent = (
        UserQuery.query
        .order_by(UserQuery.created_at.desc())
        .limit(20)
        .all()
    )

    return render_template(
        "query_insight.html",
        total_queries=total,
        recent_queries=recent,
    )

# ========= AI 洞察 API =========
@app.route("/api/insight/main_dashboard", methods=["GET"], endpoint="api_main_insight")
def api_main_insight():
    """
    main_dashboard 页的“AI 智能洞察”接口（流式 SSE）
    前端用 EventSource 连接这个接口，一边生成一边推给前端。
    """

    def generate():
        try:
            # 1. 读大屏用到的数据文件
            trend = load_json_from_static("trend.json")
            degrees = load_json_from_static("degree_counts.json")
            categories = load_json_from_static("rose.json")
            geo = load_json_from_static("geo.json")
            city_rank = load_json_from_static("city_job_rank.json")
            skills = load_json_from_static("skills_top10.json")

            months = trend.get("months", [])
            series = trend.get("series", [])
            total_series = series[0]["data"] if series else []

            degree_list = degrees.get("data", [])
            cat_list = categories
            geo_cities = geo[:30]  # 简单截一下，避免 prompt 太长
            city_top = list(zip(city_rank.get("cities", []),
                                city_rank.get("job_counts", [])))
            skill_top = list(zip(skills.get("skills", []),
                                 skills.get("counts", [])))

            # 2. 提示词：写成偏“汇报稿”的洞察
            user_prompt = f"""
你是一名资深数据分析师，正在为“AI 职场智能洞察大屏”的【总览页】撰写洞察报告。

你拿到的数据摘要如下（字段已做过聚合，只保留关键信息）：

[1] 时间趋势（AI 岗位数量）
- months: {months}
- total_job_series: {total_series}

[2] 学历结构（degree_counts）
- degree_list: {degree_list}

[3] 岗位类别结构（rose.json）
- categories(前若干个): {cat_list[:8]}

[4] 城市分布 & Top 城市
- geo 城市示例: {geo_cities[:10]}
- city_top10: {city_top[:10]}

[5] 核心技能 Top10
- skills_top10: {skill_top}

请你基于这些信息，输出一段“AI 就业市场智能洞察”，要求：

1. 输出格式按模块分三段：
   【趋势洞察】...
   【结构与地域洞察】...
   【技能与人才建议】...

2. 每一段内部用 2–3 个「· 」开头的要点进行展开说明，整体 3–5 条要点即可。
3. 风格偏实务型汇报：先给结论，再简短解释原因或数据依据，适合放进 PPT 里当讲解稿。
4. 尽量同时覆盖：时间趋势、地域差异、学历梯度、岗位方向与核心技能，对求职者给出 1–2 句实用建议。
5. 全文控制在 200～300 字左右，不要堆砌数字，也不要复述原始字段内容。

直接输出中文洞察内容即可，不要出现“上面数据”“如下所示”之类的字眼。
"""

            # 3. 调用 DeepSeek，开启流式
            stream = deepseek_client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一名擅长写简洁有力数据洞察的商业分析师，语言专业但不啰嗦。"
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    },
                ],
                stream=True
            )

            # 先发一个开始信号（可选）
            yield "data: " + json.dumps({"type": "start"}) + "\n\n"

            # 一块一块把内容推给前端
            for chunk in stream:
                delta = None
                try:
                    delta = chunk.choices[0].delta.content
                except Exception:
                    delta = None
                if not delta:
                    continue
                yield "data: " + json.dumps({"type": "chunk", "content": delta}) + "\n\n"

            # 结束标记
            yield "data: " + json.dumps({"type": "end"}) + "\n\n"

        except Exception as e:
            err_msg = f"生成洞察时后端出现错误：{str(e)}"
            yield "data: " + json.dumps({"type": "error", "content": err_msg}) + "\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/api/chat_nl", methods=["POST"])
def api_chat_nl():
    """
    自然语言问答接口：
    - 前端传入当前问题 + 简单对话历史
    - 后端读取本项目的数据文件，拼成数据摘要
    - 调用 DeepSeek 生成回答
    """
    try:
        data = request.get_json(force=True) or {}
        user_msg = data.get("message", "").strip()
        history = data.get("history", [])  # [{role:'user'/'assistant', content:'...'}, ...]

        if not user_msg:
            return jsonify({"reply": "请先输入一个问题，例如：目前哪几个城市的 AI 岗位机会最多？"}), 400

        # 1. 读数据（你已有的这些 json）
        trend = load_json_from_static("trend.json")
        degrees = load_json_from_static("degree_counts.json")
        categories = load_json_from_static("rose.json")
        geo = load_json_from_static("geo.json")
        city_rank = load_json_from_static("city_job_rank.json")
        skills = load_json_from_static("skills_top10.json")

        # 2. 做一个简短的数据摘要（不要太长）
        months = trend.get("months", [])
        series = trend.get("series", [])
        total_series = series[0]["data"] if series else []

        degree_list = degrees.get("data", [])
        cat_list = categories[:8]  # 只取前面几个类别
        geo_top_sample = geo[:15]
        city_top = list(zip(city_rank.get("cities", []),
                            city_rank.get("job_counts", [])))[:10]
        skill_top = list(zip(skills.get("skills", []),
                             skills.get("counts", [])))[:10]

        # 把这些整理成一段 summary 文本，给模型当“数据上下文”
        data_summary = f"""
[时间趋势]
- months: {months}
- total_job_series: {total_series}

[学历结构]
- degree_list: {degree_list}

[岗位类别结构（部分）]
- categories: {cat_list}

[城市分布（部分采样 + Top10）]
- geo_sample: {geo_top_sample}
- city_top10: {city_top}

[技能 Top10]
- skills_top10: {skill_top}
"""

        # 3. 组 messages：把数据 summary 放进系统/assistant，history 也带上
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个基于 AI 就业数据的智能职业顾问，只能主要参考我给你的数据摘要来回答问题。"
                    "回答时："
                    "1）尽量用通俗但专业的中文解释；"
                    "2）如果问题跟数据无关，可以给一点常识性建议，但要说明“这部分是基于通用经验”；"
                    "3）不要伪造不存在的数据，不要给出具体数字时胡编。"
                )
            },
            {
                "role": "assistant",
                "content": "以下是本系统当前的大屏数据摘要，你回答问题时要尽量依据这些信息：\n" + data_summary
            }
        ]

        # 把前端发来的 history 拼进去（简单过一遍，确保格式合法）
        for item in history[-6:]:  # 最多带最近 6 句，避免太长
            role = item.get("role")
            content = item.get("content", "")
            if role in ("user", "assistant") and content.strip():
                messages.append({"role": role, "content": content.strip()})

        # 最后加入当前这句话
        messages.append({"role": "user", "content": user_msg})

        # 4. 调用 DeepSeek（这里用非流式，接口简单一点）
        resp = deepseek_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            stream=False,
        )

        reply = resp.choices[0].message.content.strip()
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({
            "reply": "后端生成回答时出错了，可以稍后再试，或者让开发者检查日志。",
            "error": str(e)
        }), 500


@app.route("/api/chat_stream", methods=["GET"])
def api_chat_stream():
    """
    chat 页面用的流式 SSE 接口：
    - 前端用 EventSource 连接
    - 问题 q 和 history 通过 query string 传过来
    """
    from urllib.parse import unquote

    def generate():
        try:
            q = request.args.get("q", "").strip()
            history_raw = request.args.get("history") or "[]"

            try:
                history = json.loads(unquote(history_raw))
            except Exception:
                history = []

            if not q:
                yield "data: " + json.dumps({
                    "type": "error",
                    "content": "问题为空，请重新输入。"
                }) + "\n\n"
                return

            # 1. 读数据（跟 /api/chat_nl 一样）
            trend = load_json_from_static("trend.json")
            degrees = load_json_from_static("degree_counts.json")
            categories = load_json_from_static("rose.json")
            geo = load_json_from_static("geo.json")
            city_rank = load_json_from_static("city_job_rank.json")
            skills = load_json_from_static("skills_top10.json")

            months = trend.get("months", [])
            series = trend.get("series", [])
            total_series = series[0]["data"] if series else []

            degree_list = degrees.get("data", [])
            cat_list = categories[:8]
            geo_top_sample = geo[:15]
            city_top = list(zip(city_rank.get("cities", []),
                                city_rank.get("job_counts", [])))[:10]
            skill_top = list(zip(skills.get("skills", []),
                                 skills.get("counts", [])))[:10]

            data_summary = f"""
[时间趋势]
- months: {months}
- total_job_series: {total_series}

[学历结构]
- degree_list: {degree_list}

[岗位类别结构（部分）]
- categories: {cat_list}

[城市分布（部分采样 + Top10）]
- geo_sample: {geo_top_sample}
- city_top10: {city_top}

[技能 Top10]
- skills_top10: {skill_top}
"""

            messages = [
                {
                    "role": "system",
                    "content": (
                        "你是一个基于 AI 就业数据的大屏问答助手，只能主要参考我给你的数据摘要来回答问题。"
                        "回答时：1）用通俗但专业的中文；"
                        "2）超出数据部分用“基于通用经验”标记；"
                        "3）不要乱编具体数字。"
                    )
                },
                {
                    "role": "assistant",
                    "content": "以下是当前大屏的数据摘要，你回答问题时要尽量依据这些信息：\n" + data_summary
                }
            ]

            # 最近几轮对话史
            for item in history[-6:]:
                role = item.get("role")
                content = item.get("content", "")
                if role in ("user", "assistant") and content.strip():
                    messages.append({"role": role, "content": content.strip()})

            messages.append({"role": "user", "content": q})

            # 2. 流式调用 DeepSeek
            stream = deepseek_client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=messages,
                stream=True,
            )

            # 开始信号
            yield "data: " + json.dumps({"type": "start"}) + "\n\n"

            for chunk in stream:
                delta = None
                try:
                    delta = chunk.choices[0].delta.content
                except Exception:
                    delta = None
                if not delta:
                    continue

                yield "data: " + json.dumps({
                    "type": "chunk",
                    "content": delta
                }) + "\n\n"

            # 结束信号
            yield "data: " + json.dumps({"type": "end"}) + "\n\n"

        except Exception as e:
            err_msg = f"后端出错：{str(e)}"
            yield "data: " + json.dumps({
                "type": "error",
                "content": err_msg
            }) + "\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

if __name__ == '__main__':
    app.run(debug=True)
