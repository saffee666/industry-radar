"""晨报生成器：输出结构化信号清单供用户选择"""

from datetime import datetime
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent


def _priority_group(score):
    if score >= 8.0:
        return "high"
    elif score >= 6.0:
        return "mid"
    return "low"


MAX_PER_SECTION = {"high": 25, "mid": 40, "low": 50}


def generate_brief(signals, date_str=None):
    """生成晨报Markdown文件，返回文件路径"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 按优先级分组
    groups = {"high": [], "mid": [], "low": []}
    for i, s in enumerate(signals, 1):
        s["_index"] = i
        group = _priority_group(s.get("score", 0))
        groups[group].append(s)

    high = groups["high"]
    mid = groups["mid"]
    low = groups["low"]

    # 行业分布统计
    industry_count = defaultdict(int)
    type_count = defaultdict(int)
    for s in signals:
        industry_count[s.get("industry_name", "其他")] += 1
        type_count[s.get("signal_type_name", "市场端")] += 1

    lines = []
    lines.append(f"# 行业雷达晨报 — {date_str}")
    lines.append("")
    lines.append(f"## 今日概览：共收集 {len(signals)} 条信号")
    lines.append("")

    # 行业分布
    ind_summary = " · ".join(f"{k}({v})" for k, v in sorted(industry_count.items(), key=lambda x: -x[1])[:10])
    lines.append(f"**行业覆盖**: {ind_summary}")
    type_summary = " · ".join(f"{k}({v})" for k, v in sorted(type_count.items(), key=lambda x: -x[1]))
    lines.append(f"**信号类型**: {type_summary}")
    lines.append("")
    lines.append("---")
    lines.append("")

    sections = [
        ("high", "高优先级（建议必看, ≥8.0）", "🔴"),
        ("mid", "中优先级（≥6.0）", "🟡"),
        ("low", "可选关注（<6.0）", "🟢"),
    ]

    for group_key, section_title, emoji in sections:
        section_signals = groups[group_key]
        if not section_signals:
            continue

        limit = MAX_PER_SECTION[group_key]
        display = section_signals[:limit]
        omitted = len(section_signals) - len(display)

        lines.append(f"## {emoji} {section_title} ({len(display)} 条)")
        if omitted > 0:
            lines.append(f"> 另有 {omitted} 条未展示，完整数据见 output/raw/")
        lines.append("")
        lines.append("| # | 行业 | 类型 | 标题 | 评分 |")
        lines.append("|---|------|------|------|------|")

        for s in display:
            idx = s["_index"]
            ind = s.get("industry_name", "其他")
            stype = s.get("signal_type_name", "市场端")
            title = s.get("title", "")[:80]
            score = s.get("score", 0)
            lines.append(f"| {idx} | {ind} | {stype} | {title} | {score} |")

        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 📋 操作指引")
    lines.append("")
    lines.append("```")
    lines.append("python main.py analyze --ids \"1,3,5\"    # 分析选中信号")
    lines.append("python main.py analyze --ids \"all\"      # 全部分析")
    lines.append("python main.py pipeline                  # 交互式管线")
    lines.append("```")
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    brief_md = "\n".join(lines)

    # 保存
    brief_path = PROJECT_ROOT / "output" / "briefs" / f"brief_{date_str}.md"
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(brief_md, encoding="utf-8")

    return str(brief_path)


if __name__ == "__main__":
    # 测试用
    test_signals = [
        {"title": "DeepSeek开源新模型性能直逼GPT-5，API价格骤降80%", "industry_name": "AI/大模型", "signal_type_name": "技术端", "score": 9.2},
        {"title": "东南亚电商新政策出台，中国卖家注册量单月暴增300%", "industry_name": "出海/跨境", "signal_type_name": "机会端", "score": 8.8},
        {"title": "Boss直聘AI岗位同比+150%，大模型工程师月薪中位数45K", "industry_name": "AI/大模型", "signal_type_name": "需求端", "score": 8.5},
        {"title": "某短剧平台日活破千万，微短剧制作需求暴涨", "industry_name": "短剧/内容", "signal_type_name": "市场端", "score": 7.2},
        {"title": "新能源光伏组件价格触底反弹，行业或迎拐点", "industry_name": "新能源", "signal_type_name": "市场端", "score": 6.8},
        {"title": "GitHub上新晋万星项目：AI Agent开发框架", "industry_name": "AI/大模型", "signal_type_name": "技术端", "score": 6.5},
        {"title": "小红书AI绘画话题浏览量破10亿", "industry_name": "AI/大模型", "signal_type_name": "需求端", "score": 5.8},
        {"title": "拉勾网显示Web3岗位需求周增25%", "industry_name": "Web3/Crypto", "signal_type_name": "需求端", "score": 4.5},
    ]

    path = generate_brief(test_signals)
    print(Path(path).read_text(encoding="utf-8"))
