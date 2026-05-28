"""深度分析引擎：选中信号 → 多源交叉验证 → AI分析 → 日报"""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Windows GBK 终端兼容
def _safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        print(*(str(a).encode('ascii', errors='replace').decode('ascii') for a in args), **kwargs)

PROJECT_ROOT = Path(__file__).parent.parent


def _search_cross_validate(signal, max_results=5):
    """用DDG + Bing搜索做交叉验证，返回补充信息"""
    title = signal.get("title", "")
    industry = signal.get("industry_name", "")

    results = {"ddg": [], "bing": [], "playwright_sources": []}

    # 使用 DDG 搜索交叉验证
    ddgs_module = None
    try:
        from ddgs import DDGS as _DDGS1
        ddgs_module = _DDGS1
    except ImportError:
        try:
            from duckduckgo_search import DDGS as _DDGS2
            ddgs_module = _DDGS2
        except ImportError:
            pass

    if ddgs_module:
        try:
            with ddgs_module() as ddgs:
                r = list(ddgs.text(f"{title} {industry}", max_results=max_results))
                results["ddg"] = [{"title": x.get("title", ""), "url": x.get("href", ""), "snippet": x.get("body", "")} for x in r]
        except Exception:
            pass

    return results


def _analyze_signal_with_claude(signal, cross_refs):
    """使用 Claude 分析单个信号——调用 claude CLI（非交互模式）"""
    title = signal.get("title", "")
    snippet = signal.get("snippet", "")
    industry = signal.get("industry_name", "")
    stype = signal.get("signal_type_name", "")
    score = signal.get("score", 0)
    url = signal.get("url", "")
    metadata = signal.get("metadata", {})

    # 构建分析prompt
    prompt_parts = [
        f"分析以下行业信号，用中文回答，结构如下：",
        f"",
        f"信号: {title}",
        f"行业: {industry} | 信号类型: {stype} | 评分: {score}/10",
        f"来源: {url}",
        f"摘要: {snippet}",
        f"元数据: {json.dumps(metadata, ensure_ascii=False)}",
        f"",
        f"请按以下6段输出分析（每段2-4句，简洁有力）：",
        f"",
        f"1. **事实确认**: 这个信号是否可靠？从多个来源交叉验证的结果如何？",
        f"2. **商业解读**: 这个变化为什么重要？背后的商业逻辑是什么？",
        f"3. **机会评估**: 对于个人/小团队/小公司有什么机会？市场规模如何？入场时机是否合适？",
        f"4. **行动建议**: 具体可以做什么？第一步是什么？需要什么资源和技能？",
        f"5. **风险提示**: 有什么不确定因素？可能的风险是什么？",
        f"6. **持续追踪**: 接下来需要关注什么指标/信号来验证这个趋势？",
    ]

    prompt = "\n".join(prompt_parts)

    # 尝试通过 claude CLI 调用
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--print", "--output-format", "text", "--max-tokens", "1500"],
            capture_output=True, text=True, timeout=120, cwd=str(PROJECT_ROOT)
        )
        if result.returncode == 0 and result.stdout.strip():
            return prompt, result.stdout.strip()
    except FileNotFoundError:
        pass
    except Exception as e:
        _safe_print(f"   Claude调用异常: {e}")

    # Fallback: 返回prompt供手动分析
    return prompt, None


def _generate_chart_data(signals):
    """生成图表数据（行业分布饼图 + 评分分布直方图）"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import numpy as np

    date_str = datetime.now().strftime("%Y-%m-%d")
    chart_dir = PROJECT_ROOT / "output" / "reports" / f"charts_{date_str}"
    chart_dir.mkdir(parents=True, exist_ok=True)

    # 找中文字体
    zh_fonts = [f for f in fm.fontManager.ttflist if any(
        k in f.name.lower() for k in ["simhei", "simsun", "microsoft yahei", "noto sans cjk", "wenquanyi", "source han", "heiti", "songti"]
    )]
    if zh_fonts:
        font_family = zh_fonts[0].name
        font_prop = fm.FontProperties(family=font_family)
        plt.rcParams['font.sans-serif'] = [font_family, 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    else:
        font_prop = None

    # 1. 行业分布饼图
    industries = defaultdict(int)
    for s in signals:
        industries[s.get("industry_name", "其他")] += 1

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    labels = list(industries.keys())
    sizes = list(industries.values())
    colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))

    wedges, texts, autotexts = axes[0].pie(
        sizes, labels=labels, autopct="%1.1f%%",
        colors=colors, startangle=90,
        textprops={"fontproperties": font_prop} if font_prop else {}
    )
    axes[0].set_title("行业分布", fontproperties=font_prop if font_prop else None, fontsize=14)

    # 2. 评分分布直方图
    scores = [s.get("score", 0) for s in signals]
    axes[1].hist(scores, bins=10, color="#4A90D9", edgecolor="white", alpha=0.8)
    axes[1].set_xlabel("评分", fontproperties=font_prop if font_prop else None)
    axes[1].set_ylabel("信号数量", fontproperties=font_prop if font_prop else None)
    axes[1].set_title("信号评分分布", fontproperties=font_prop if font_prop else None, fontsize=14)
    axes[1].axvline(x=7.0, color="red", linestyle="--", alpha=0.5, label="高优线")
    axes[1].legend()

    plt.tight_layout()
    chart_path = chart_dir / f"overview_{date_str}.png"
    plt.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close()

    return str(chart_dir)


def analyze_signals(selected_signals, date_str=None):
    """深度分析选中信号，生成日报Markdown"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    _safe_print(f"\n[深度分析] {len(selected_signals)} 条信号...")

    # 生成概览图表
    try:
        chart_dir = _generate_chart_data(selected_signals)
        _safe_print(f"[图表] 已生成: {chart_dir}")
    except Exception as e:
        _safe_print(f"[图表] 生成失败: {e}")
        chart_dir = None

    # 按行业分组
    by_industry = defaultdict(list)
    for s in selected_signals:
        by_industry[s.get("industry_name", "其他")].append(s)

    # 生成日报
    lines = []
    lines.append(f"# 📊 行业雷达深度日报 — {date_str}")
    lines.append("")

    # 执行摘要
    lines.append("## 执行摘要")
    lines.append("")

    high_priority = [s for s in selected_signals if s.get("score", 0) >= 7.0]
    top_industries = sorted(by_industry.keys(), key=lambda k: len(by_industry[k]), reverse=True)[:5]
    top_types = defaultdict(int)
    for s in selected_signals:
        top_types[s.get("signal_type_name", "")] += 1
    top_type = max(top_types, key=top_types.get) if top_types else ""

    lines.append(f"今日深度分析 **{len(selected_signals)}** 条信号，覆盖 **{len(by_industry)}** 个行业。")
    if high_priority:
        lines.append(f"其中高优先级信号 **{len(high_priority)}** 条，涉及 {', '.join(top_industries[:3])} 等行业。")
    lines.append(f"信号类型以 **{top_type}** 为主。")
    lines.append("")

    # 信号类型概览
    lines.append("### 信号类型分布")
    lines.append("")
    for stype, count in sorted(top_types.items(), key=lambda x: -x[1]):
        lines.append(f"- **{stype}**: {count} 条")
    lines.append("")

    if chart_dir:
        lines.append(f"![行业概览](charts_{date_str}/overview_{date_str}.png)")
        lines.append("")

    lines.append("---")
    lines.append("")

    # 按行业逐条分析
    for industry in sorted(by_industry.keys()):
        industry_signals = by_industry[industry]
        lines.append(f"## {industry}")
        lines.append("")

        for i, signal in enumerate(industry_signals, 1):
            title = signal.get("title", "")
            stype = signal.get("signal_type_name", "")
            score = signal.get("score", 0)
            snippet = signal.get("snippet", "")
            url = signal.get("url", "")
            metadata = signal.get("metadata", {})

            lines.append(f"### 信号 {i}: {title}")
            lines.append("")
            lines.append(f"**类型**: {stype} | **评分**: {score}/10")
            lines.append(f"**来源**: [{signal.get('source_name', '')}]({url})")
            lines.append("")

            # 交叉验证
            lines.append("#### 📡 多源交叉验证")
            try:
                cross_refs = _search_cross_validate(signal)
                if cross_refs.get("ddg"):
                    lines.append("来自 DuckDuckGo 的验证结果:")
                    for ref in cross_refs["ddg"][:3]:
                        lines.append(f"- [{ref['title'][:50]}]({ref['url']}): {ref['snippet'][:100]}")
                else:
                    lines.append("（DDG验证未返回结果，建议手动验证）")
            except Exception:
                lines.append("（交叉验证暂不可用）")
            lines.append("")

            # AI分析
            lines.append("#### 🤖 AI深度分析")
            lines.append("")
            prompt, analysis = _analyze_signal_with_claude(signal, None)

            if analysis:
                lines.append(analysis)
            else:
                lines.append("> ⚠️ Claude CLI 未可用，以下为分析框架。可手动运行：")
                lines.append("> ```")
                lines.append(f"> claude -p \"分析行业信号: {title}\" --print")
                lines.append("> ```")
                lines.append("")
                # 输出基本分析框架
                lines.append("**事实确认**: 待验证")
                lines.append("**商业解读**: 待分析")
                lines.append("**机会评估**: 待评估")
                lines.append("**行动建议**: 待生成")
                lines.append("**风险提示**: 待评估")
                lines.append("**持续追踪**: 待定义")

            lines.append("")
            lines.append("---")
            lines.append("")

    # 附录
    lines.append("## 附录")
    lines.append("")
    lines.append("### 全部信号索引")
    lines.append("")
    lines.append("| # | 行业 | 类型 | 标题 | 评分 |")
    lines.append("|---|------|------|------|------|")
    for i, s in enumerate(selected_signals, 1):
        lines.append(f"| {i} | {s.get('industry_name', '')} | {s.get('signal_type_name', '')} | {s.get('title', '')[:50]} | {s.get('score', 0)} |")
    lines.append("")

    lines.append("### 数据来源清单")
    sources = set(s.get("source_name", "") for s in selected_signals)
    for src in sorted(sources):
        lines.append(f"- {src}")
    lines.append("")

    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"> 分析信号数: {len(selected_signals)} | 覆盖行业: {len(by_industry)}")

    report_md = "\n".join(lines)

    # 保存
    report_path = PROJECT_ROOT / "output" / "reports" / f"report_{date_str}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_md, encoding="utf-8")

    return str(report_path)


if __name__ == "__main__":
    test_signals = [
        {"title": "DeepSeek开源新模型", "industry_name": "AI/大模型", "signal_type_name": "技术端", "score": 9.2, "snippet": "API价格骤降", "url": "https://example.com/1", "source_name": "GitHub Trending", "metadata": {}, "category": "tech_communities"},
        {"title": "东南亚电商风口", "industry_name": "出海/跨境", "signal_type_name": "机会端", "score": 8.8, "snippet": "新政策红利", "url": "https://example.com/2", "source_name": "36氪", "metadata": {}, "category": "policy_media"},
    ]
    path = analyze_signals(test_signals, "2026-05-27")
    print(f"\n日报: {path}")
