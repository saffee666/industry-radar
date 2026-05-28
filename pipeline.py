#!/usr/bin/env python3
"""交互式完整管线 — 半自动人机协同"""

import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent


def run_pipeline():
    """交互式全管线：采集→处理→晨报→选择→深度分析"""
    from main import cmd_collect, cmd_process, cmd_brief
    from reports.deep_analysis import analyze_signals

    print("=" * 60)
    print("   🛰️  行业雷达 · 交互式管线")
    print("   自动采集 → 你选信号 → 深度分析")
    print("=" * 60)

    # Phase 1-2: 采集 + 处理 + 晨报
    print("\n📡 Phase 1-2: 自动采集 & 处理...\n")
    date_str = datetime.now().strftime("%Y-%m-%d")

    try:
        signals = cmd_collect(None)
        if not signals:
            print("❌ 未采集到信号")
            return
    except Exception as e:
        print(f"❌ 采集失败: {e}")
        return

    cmd_process(None)

    brief_path = cmd_brief(None)

    # 输出晨报内容供阅读
    print("\n" + "=" * 60)
    brief_content = Path(brief_path).read_text(encoding="utf-8")
    print(brief_content)

    # Phase 3: 用户选择
    print("\n" + "=" * 60)
    print("🎯 请选择要深度分析的信号")
    print("   输入编号(逗号分隔如 1,3,5) | all=全部 | q=退出")
    print("=" * 60)

    choice = input("\n👉 你的选择: ").strip()
    if choice.lower() == "q":
        print("👋 已退出，晨报已保存可稍后查看")
        return

    # 解析选择
    processed_file = PROJECT_ROOT / "output" / "raw" / f"processed_{date_str}.json"
    all_signals = json.loads(processed_file.read_text(encoding="utf-8"))

    if choice.lower() == "all":
        selected = all_signals
    else:
        ids = [int(x.strip()) - 1 for x in choice.split(",") if x.strip().isdigit()]
        selected = [all_signals[i] for i in ids if 0 <= i < len(all_signals)]

    if not selected:
        print("❌ 没有选中任何信号")
        return

    print(f"\n🔍 开始深度分析 {len(selected)} 条信号...")

    # Phase 4: 深度分析
    report_path = analyze_signals(selected, date_str)

    # Phase 5: 完成
    print("\n" + "=" * 60)
    print("✅ 全管线完成！")
    print(f"📊 深度日报: {report_path}")
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()
