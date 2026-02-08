#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟手机端访问首页，截取第二个 section（推荐方案）并保存。

使用前请先安装：
  pip install playwright
  playwright install chromium

然后在一个终端启动 Web 应用：
  python web_app.py

在另一个终端运行本脚本（在项目根目录）：
  python scripts/screenshot.py

可选：指定 URL，默认 http://127.0.0.1:8000
  python scripts/screenshot.py --url https://ssq.webyoung.cn
"""

import argparse
import os
import sys
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="手机端截取首页第二个 section")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="页面 URL，默认 http://127.0.0.1:8000",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="输出图片路径，默认 pics/ssq_r日期.png",
    )
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("请先安装: pip install playwright && playwright install chromium")
        sys.exit(1)

    date_str = datetime.now().strftime("%Y%m%d")
    default_name = f"ssq_r{date_str}.png"
    out = args.output or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "pics",
        default_name,
    )
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        # 模拟手机视口（宽 430px，高 932px）
        context = browser.new_context(
            viewport={"width": 430, "height": 932},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        )
        page = context.new_page()
        page.goto(args.url, wait_until="networkidle", timeout=15000)
        # 等待第二个 section 有内容（推荐方案渲染完）
        page.wait_for_selector("#result-container", state="visible", timeout=5000)
        page.wait_for_timeout(800)
        # 第二个 section：main 下第二个 .card（推荐方案）
        section = page.locator("main .card").nth(1)
        section.screenshot(path=out)
        browser.close()

    print(f"已保存: {out}")


if __name__ == "__main__":
    main()
