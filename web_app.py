#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单Web前端 + API，用于展示双色球智能推荐方案

功能：
- 手机适配的Web页面（参考 cp.webyoung.cn 的交互风格）
- 支持可选红胆、蓝胆（拖胆）输入
- 后端复用 DoubleColorBallAnalyzer 的推荐与增强方案逻辑
"""

from __future__ import annotations

import os
import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from flask import Flask, render_template, request, jsonify

from scripts.lottery_analyzer import DoubleColorBallAnalyzer


app = Flask(__name__, template_folder="templates", static_folder="static")


@app.context_processor
def inject_current_year():
    """让所有模板可直接使用 current_year，避免模板里使用未传入的 datetime 报错。"""
    return {"current_year": datetime.now(timezone.utc).year}


def get_analyzer() -> DoubleColorBallAnalyzer:
    """获取全局双色球分析器实例，并确保历史数据已初始化更新。"""
    # 简单的惰性初始化，全局只创建一个实例
    if not hasattr(app, "_dc_analyzer"):
        analyzer = DoubleColorBallAnalyzer()
        analyzer.init_and_update_history()
        app._dc_analyzer = analyzer
    return app._dc_analyzer  # type: ignore[attr-defined]


def parse_dan_input(raw: str, max_num: int) -> List[int]:
    """解析前端传入的胆号字符串，如 '1,3,08' -> [1, 3, 8]，并做范围校验去重。"""
    if not raw:
        return []
    parts = [p.strip() for p in raw.replace("，", ",").split(",") if p.strip()]
    nums: List[int] = []
    for p in parts:
        try:
            n = int(p)
        except ValueError:
            continue
        if 1 <= n <= max_num and n not in nums:
            nums.append(n)
    return nums


@app.route("/", methods=["GET"])
def index():
    """首页：表单 + 推荐结果展示."""
    analyzer = get_analyzer()
    latest_period = analyzer.lottery_data[0]["period"] if analyzer.lottery_data else "N/A"
    latest_date = analyzer.lottery_data[0]["date"] if analyzer.lottery_data else "N/A"

    # 最近10期开奖，用于页面下方展示
    recent_draws = []
    for rec in analyzer.lottery_data[:10]:
        recent_draws.append(
            {
                "period": rec.get("period"),
                "date": rec.get("date"),
                "red_balls": rec.get("red_balls", []),
                "blue_ball": rec.get("blue_ball"),
            }
        )

    # 默认不带拖胆，直接生成一版方案用于初始展示
    enhanced_plan = analyzer.generate_enhanced_plan_with_combos(
        recommendations=analyzer.generate_recommendations(num_sets=8),
        red_dan=None,
        blue_dan=None,
        silent=True,
    )

    return render_template(
        "index.html",
        latest_period=latest_period,
        latest_date=latest_date,
        enhanced_plan=enhanced_plan,
        recent_draws=recent_draws,
    )


@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    """
    API: 根据可选红胆、蓝胆生成推荐方案。

    请求(JSON 或 form)字段：
    - red_dan: 可选，字符串，如 "1,3,8"
    - blue_dan: 可选，字符串，如 "2,9"

    响应(JSON)：
    {
      "latest_period": "...",
      "latest_date": "...",
      "plan": {
        "singles_6_1": [...],
        "combo_7_1": {...},
        "combo_6_2": {...}
      }
    }
    """
    analyzer = get_analyzer()

    data = request.get_json(silent=True) or request.form
    red_dan_raw = data.get("red_dan", "") if data else ""
    blue_dan_raw = data.get("blue_dan", "") if data else ""
    strategies_raw = data.get("strategies", [])

    red_dan = parse_dan_input(red_dan_raw, max_num=33)
    blue_dan = parse_dan_input(blue_dan_raw, max_num=16)

    # 非法约束：红胆最多 5 个（6+1 需 6 红），蓝胆最多 1 个；超出则按未上送处理
    if len(red_dan) > 5:
        red_dan = []
    if len(blue_dan) > 1:
        blue_dan = []

    # 先生成8种策略推荐，再带入增强方案（支持拖胆约束）
    recommendations = analyzer.generate_recommendations(num_sets=8)
    # 如果前端指定了策略过滤，则按策略名称过滤单式组合
    if strategies_raw:
        if isinstance(strategies_raw, str):
            # 兼容 form-urlencoded 传法：单个字符串也按逗号拆分
            strategies = [s.strip() for s in strategies_raw.split(",") if s.strip()]
        else:
            strategies = [str(s).strip() for s in strategies_raw if str(s).strip()]
        filtered = [r for r in recommendations if r.get("strategy") in strategies]
        if filtered:
            recommendations = filtered

    plan = analyzer.generate_enhanced_plan_with_combos(
        recommendations=recommendations,
        red_dan=red_dan or None,
        blue_dan=blue_dan or None,
        silent=True,
    )

    latest_period = analyzer.lottery_data[0]["period"] if analyzer.lottery_data else "N/A"
    latest_date = analyzer.lottery_data[0]["date"] if analyzer.lottery_data else "N/A"

    return jsonify(
        {
            "latest_period": latest_period,
            "latest_date": latest_date,
            "plan": plan,
        }
    )


@app.route("/history", methods=["GET"])
def history():
    """历史开奖数据分页展示页面。"""
    analyzer = get_analyzer()
    records = analyzer.lottery_data or []

    per_page = 50
    try:
        page = int(request.args.get("page", "1"))
    except ValueError:
        page = 1
    page = max(page, 1)

    total = len(records)
    pages = max(math.ceil(total / per_page), 1) if total else 1
    if page > pages:
        page = pages

    start = (page - 1) * per_page
    end = start + per_page
    page_records = records[start:end]

    return render_template(
        "history.html",
        records=page_records,
        page=page,
        pages=pages,
        total=total,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # 默认在 0.0.0.0 监听，方便容器或局域网访问
    app.run(host="0.0.0.0", port=port, debug=True)

