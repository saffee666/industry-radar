from datetime import datetime
from src.models import AnalyzedSignal, DailyBrief
from src.pipeline.scorer import (
    top_opportunities, by_industry, high_priority, medium_priority, rank_signals
)


PRIORITY_ICONS = {
    range(9, 11): "🔴",
    range(8, 9): "🟠",
    range(7, 8): "🟡",
    range(0, 7): "⚪",
}


def _icon(score: float) -> str:
    for r, icon in PRIORITY_ICONS.items():
        if score >= r.start and score < r.stop:
            return icon
    return "⚪"


def format_brief(signals: list[AnalyzedSignal], total_collected: int, total_filtered: int) -> str:
    date_str = datetime.now().strftime("%Y-%m-%d")
    ranked = rank_signals(signals)
    opps = top_opportunities(ranked, n=5)
    industries = by_industry(ranked)
    high = high_priority(ranked)
    med = medium_priority(ranked)

    lines = []
    lines.append(f"# 行业雷达晨报 — {date_str}")
    lines.append("")

    # Overview
    lines.append("## 今日概览")
    lines.append("")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 采集信号 | {total_collected} |")
    lines.append(f"| 过滤后 | {total_filtered} |")
    lines.append(f"| 高优先级 (>=8.0) | {len(high)} |")
    lines.append(f"| 中优先级 (>=6.0) | {len(med)} |")
    lines.append("")

    # Industry distribution
    ind_parts = []
    for code, sigs in industries.items():
        name = sigs[0].industry_name if sigs else code
        ind_parts.append(f"{name}({len(sigs)})")
    lines.append(f"**行业分布:** {' · '.join(ind_parts[:8])}")
    lines.append("")

    # Layer 1: Today's Opportunities
    lines.append("---")
    lines.append("")
    lines.append("## 今日机会")
    lines.append("")
    if opps:
        lines.append("*以下是今日评分最高的5条套利信号，每条包含详细分析和行动建议。*")
        lines.append("")

        for i, s in enumerate(opps, 1):
            icon = _icon(s.composite_score)
            lines.append(f"### {i}. {icon} {s.title}")
            lines.append("")
            lines.append(f"| 维度 | 评分 |")
            lines.append(f"|------|------|")
            lines.append(f"| 综合评分 | **{s.composite_score}** |")
            lines.append(f"| 需求真实性 | {s.demand_score} |")
            lines.append(f"| 供给缺口度 | {s.supply_gap_score} |")
            lines.append(f"| 窗口紧迫性 | {s.window_score} |")
            lines.append(f"| 变现直接性 | {s.monetization_score} |")
            lines.append(f"| 进入可行性 | {s.feasibility_score} |")
            lines.append("")
            lines.append(f"- **行业:** {s.industry_name} | **类型:** {s.signal_type_name}")
            lines.append(f"- **为什么重要:** {s.why_important}")
            lines.append(f"- **窗口期:** {s.window_estimate}")
            lines.append(f"- **建议行动:** {s.suggested_action}")
            lines.append(f"- **风险提示:** {s.risk_note}")
            if s.url:
                lines.append(f"- **来源:** [{s.source_name}]({s.url})")
            lines.append("")
    else:
        lines.append("*今日无高价值机会信号。*")
        lines.append("")

    # Layer 2: Industry Signals
    lines.append("---")
    lines.append("")
    lines.append("## 行业信号")
    lines.append("")

    # Top 20 by score across all industries
    top20 = ranked[:20]
    lines.append("| # | 行业 | 类型 | 标题 | 评分 | 判断 |")
    lines.append("|---|------|------|------|------|------|")
    for i, s in enumerate(top20, 1):
        icon = _icon(s.composite_score)
        title_short = s.title[:35] + ("..." if len(s.title) > 35 else "")
        judgment = s.why_important[:25] + ("..." if len(s.why_important) > 25 else "")
        lines.append(
            f"| {i} | {icon} {s.industry_name} | {s.signal_type_name} | "
            f"{title_short} | **{s.composite_score}** | {judgment} |"
        )
    lines.append("")

    # By industry breakdown
    for code, sigs in industries.items():
        name = sigs[0].industry_name if sigs else code
        if name == "其他" and len(sigs) < 3:
            continue
        lines.append(f"### {name} ({len(sigs)}条)")
        lines.append("")
        for s in sigs[:5]:
            icon = _icon(s.composite_score)
            judgment = s.why_important or s.suggested_action or ""
            lines.append(f"- {icon} **[{s.title}]({s.url})** [{s.composite_score}] — {judgment}")
        if len(sigs) > 5:
            lines.append(f"- *...另有 {len(sigs) - 5} 条*")
        lines.append("")

    # Layer 3: Anomalies (placeholder for v2)
    lines.append("---")
    lines.append("")
    lines.append("## 异常信号")
    lines.append("")
    lines.append("*异常监测将在v2版本上线（跨天趋势对比+关键词突升检测）。*")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                 f"采集 {total_collected} → 过滤后 {total_filtered} → "
                 f"高价值 {len(high)} 条")
    lines.append("")
    lines.append("> 评分说明: 综合分≥8.0为高优先级(建议关注)，6.0-7.9为中优先级(了解即可)，<6.0为低优先级。")
    lines.append("> 评分模式: 自己做项目(需求25%+供给25%+窗口15%+变现15%+可行性20%)")

    return "\n".join(lines)
