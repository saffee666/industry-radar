#!/usr/bin/env python3
"""行业雷达 CLI — 每日行业信号采集、筛选、深度分析"""

import argparse
import sys
import json
from datetime import datetime
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).parent

# Windows GBK终端兼容
def _p(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        print(*(str(a).encode('ascii', errors='replace').decode('ascii') for a in args), **kwargs)


def cmd_collect(args):
    """全源信号采集"""
    from collectors.tech_communities import collect_tech_communities
    from collectors.chinese_platforms import collect_chinese_platforms
    from collectors.freelance_markets import collect_freelance_markets
    from collectors.job_markets import collect_job_markets
    from collectors.search_trends import collect_search_trends
    from collectors.policy_media import collect_policy_media

    _p("[行业雷达] 全源信号采集")
    _p("=" * 50)

    all_signals = []

    collectors = [
        ("技术社区", collect_tech_communities),
        ("中文平台", collect_chinese_platforms),
        ("交易/接单", collect_freelance_markets),
        ("招聘市场", collect_job_markets),
        ("搜索趋势", collect_search_trends),
        ("政策/媒体", collect_policy_media),
    ]

    for name, func in collectors:
        _p(f"\n  [{name}] 采集中...")
        try:
            signals = func()
            all_signals.extend(signals)
            _p(f"     [OK] {name}: {len(signals)} 条信号")
        except Exception as e:
            _p(f"     [WARN] {name}: 采集异常 - {e}")

    _p(f"\n[统计] 总计采集: {len(all_signals)} 条原始信号")

    date_str = datetime.now().strftime("%Y-%m-%d")
    raw_file = PROJECT_ROOT / "output" / "raw" / f"signals_{date_str}.json"
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file.write_text(json.dumps(all_signals, ensure_ascii=False, indent=2), encoding="utf-8")
    _p(f"[保存] 原始数据已保存: {raw_file}")

    return all_signals


def cmd_process(args):
    """信号处理：去重 + 分类 + 打分"""
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    raw_file = PROJECT_ROOT / "output" / "raw" / f"signals_{date_str}.json"

    if not raw_file.exists():
        _p(f"[ERROR] 未找到 {date_str} 的原始数据，请先运行 collect")
        sys.exit(1)

    raw_signals = json.loads(raw_file.read_text(encoding="utf-8"))
    _p(f"[加载] {len(raw_signals)} 条原始信号")

    from processors.dedup import deduplicate
    from processors.classifier import classify_signals
    from processors.scorer import score_signals

    unique = deduplicate(raw_signals)
    _p(f"[去重] 后: {len(unique)} 条")

    classified = classify_signals(unique)
    _p(f"[分类] 完成")

    scored = score_signals(classified)
    _p(f"[评分] 排序完成")

    processed_file = PROJECT_ROOT / "output" / "raw" / f"processed_{date_str}.json"
    processed_file.write_text(json.dumps(scored, ensure_ascii=False, indent=2), encoding="utf-8")
    _p(f"[保存] 处理后数据: {processed_file}")

    industries = Counter(s["industry"] for s in scored)
    types = Counter(s["signal_type"] for s in scored)
    _p(f"\n[统计] 行业分布: {dict(industries)}")
    _p(f"[统计] 信号类型: {dict(types)}")

    return scored


def cmd_brief(args):
    """生成晨报"""
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    processed_file = PROJECT_ROOT / "output" / "raw" / f"processed_{date_str}.json"

    if not processed_file.exists():
        _p(f"[ERROR] 未找到 {date_str} 的处理后数据，请先运行 process")
        sys.exit(1)

    signals = json.loads(processed_file.read_text(encoding="utf-8"))
    from reports.morning_brief import generate_brief
    brief_path = generate_brief(signals, date_str)
    _p(f"[晨报] 已生成: {brief_path}")
    return brief_path


def cmd_analyze(args):
    """深度分析选中信号"""
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    processed_file = PROJECT_ROOT / "output" / "raw" / f"processed_{date_str}.json"

    if not processed_file.exists():
        _p(f"[ERROR] 未找到 {date_str} 的处理后数据，请先运行 process")
        sys.exit(1)

    signals = json.loads(processed_file.read_text(encoding="utf-8"))

    if args.ids.lower() == "all":
        selected = signals
    else:
        ids = [int(x.strip()) - 1 for x in args.ids.split(",") if x.strip().isdigit()]
        selected = [signals[i] for i in ids if 0 <= i < len(signals)]

    if not selected:
        _p("[ERROR] 没有有效的信号选中")
        sys.exit(1)

    _p(f"[选中] {len(selected)} 条信号进行深度分析")
    from reports.deep_analysis import analyze_signals
    report_path = analyze_signals(selected, date_str)
    _p(f"[日报] 深度日报已生成: {report_path}")
    return report_path


def cmd_full(args):
    """一键全流程：采集 → 处理 → 晨报"""
    signals = cmd_collect(args)
    if not signals:
        _p("[ERROR] 未采集到信号，终止")
        return

    cmd_process(args)
    brief_path = cmd_brief(args)

    _p("\n" + "=" * 50)
    _p("[完成] 全流程完成!")
    _p(f"[晨报] {brief_path}")
    _p(f"[提示] 下一步: python main.py analyze --ids \"1,3,5\"")


def main():
    parser = argparse.ArgumentParser(
        description="行业雷达 - 每日行业信号雷达",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py collect                # 全源采集
  python main.py process                # 信号处理(去重+分类+打分)
  python main.py brief                  # 生成晨报
  python main.py analyze --ids "1,3,5"  # 深度分析选中信号
  python main.py full                   # 一键全流程
  python main.py pipeline               # 交互式完整管线
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    subparsers.add_parser("collect", help="全源信号采集")
    subparsers.add_parser("process", help="信号处理(去重+分类+打分)")
    subparsers.add_parser("brief", help="生成晨报")

    analyze_parser = subparsers.add_parser("analyze", help="深度分析选中信号")
    analyze_parser.add_argument("--ids", type=str, default="all",
                                help="信号编号逗号分隔, 如 '1,3,5' 或 'all'")

    subparsers.add_parser("full", help="一键全流程(collect+process+brief)")
    subparsers.add_parser("pipeline", help="交互式完整管线")

    for sp_name in ["collect", "process", "brief", "analyze", "full", "pipeline"]:
        sp = subparsers.choices.get(sp_name)
        if sp:
            sp.add_argument("--date", type=str, help="指定日期 YYYY-MM-DD")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "collect": lambda: cmd_collect(args),
        "process": lambda: cmd_process(args),
        "brief": lambda: cmd_brief(args),
        "analyze": lambda: cmd_analyze(args),
        "full": lambda: cmd_full(args),
        "pipeline": lambda: (__import__("pipeline").run_pipeline()),
    }
    commands[args.command]()


if __name__ == "__main__":
    main()
