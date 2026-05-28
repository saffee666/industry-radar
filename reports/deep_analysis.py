"""深度分析引擎 v2：选中信号 → 多源交叉验证 → 结构化分析 → 日报"""

import json
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

OUTPUT_DIR = Path("D:/claude产出/industry-radar/reports")

# === 搜索验证 ===

def _search_ddg(query, max_results=5):
    """DDG 搜索，返回结果列表"""
    results = []
    for lib in ("ddgs", "duckduckgo_search"):
        try:
            module = __import__(lib, fromlist=["DDGS"])
            with module.DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", "")[:200],
                    })
            if results:
                break
        except Exception:
            continue
    return results


def _cross_validate(signal):
    """对单条信号做多源搜索验证"""
    title = signal.get("title", "")
    industry = signal.get("industry_name", "")

    queries = [
        title[:80],
        f"{title[:60]} {industry}",
    ]
    all_results = []

    for q in queries:
        ddg_results = _search_ddg(q, max_results=3)
        all_results.extend(ddg_results)

    # 去重
    seen = set()
    unique = []
    for r in all_results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)
    return unique[:8]


# === 信号预处理 ===

def _extract_keywords(title, snippet="", max_kw=6):
    """从标题提取关键词用于搜索"""
    text = f"{title} {snippet}"
    # 提取中文词组（2-4字连续）
    zh_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
    # 提取英文单词（3+字母）
    en_words = re.findall(r'[a-zA-Z]{3,}', text)

    # 去重并过滤停用词
    stopwords = {"一个", "这个", "那个", "什么", "怎么", "为什么", "可以", "没有",
                 "已经", "还是", "只是", "如果", "因为", "所以", "但是", "然而",
                 "the", "and", "for", "that", "this", "with", "from", "have"}
    keywords = []
    seen = set()
    for w in zh_words + en_words:
        wl = w.lower()
        if wl not in stopwords and wl not in seen:
            seen.add(wl)
            keywords.append(w)
    return keywords[:max_kw]


# === 主分析函数 ===

def analyze_signals(selected_signals, date_str=None):
    """深度分析选中信号，生成日报Markdown和搜索提示"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"\n[深度分析] {len(selected_signals)} 条信号")

    # 按行业分组
    by_industry = defaultdict(list)
    for s in selected_signals:
        by_industry[s.get("industry_name", "其他")].append(s)

    lines = []
    lines.append(f"# 行业雷达深度日报 — {date_str}")
    lines.append("")
    lines.append(f"> 分析信号数: {len(selected_signals)} | 覆盖行业: {len(by_industry)}")
    lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # === 执行摘要 ===
    lines.append("## 执行摘要")
    lines.append("")

    high = [s for s in selected_signals if s.get("score", 0) >= 8.0]
    mid = [s for s in selected_signals if 6.0 <= s.get("score", 0) < 8.0]
    top_inds = sorted(by_industry.keys(), key=lambda k: len(by_industry[k]), reverse=True)[:5]
    type_counts = defaultdict(int)
    for s in selected_signals:
        type_counts[s.get("signal_type_name", "")] += 1
    top_type = max(type_counts, key=type_counts.get) if type_counts else ""

    lines.append(f"今日选中 **{len(selected_signals)}** 条信号深度分析。")
    lines.append(f"其中高优先级 **{len(high)}** 条（≥8.0），中优先级 **{len(mid)}** 条（6.0-7.9）。")
    lines.append(f"覆盖行业: {'、'.join(top_inds)}。")
    lines.append(f"信号类型以 **{top_type}** 为主（{type_counts.get(top_type, 0)} 条）。")
    lines.append("")

    # 信号类型分布
    lines.append("### 类型概览")
    for st, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        bar = "█" * min(cnt, 20)
        lines.append(f"- {st}: {bar} ({cnt})")
    lines.append("")

    # 行业概览
    lines.append("### 行业分布")
    for ind in top_inds:
        ind_signals = by_industry[ind]
        avg_score = sum(s.get("score", 0) for s in ind_signals) / len(ind_signals)
        lines.append(f"- **{ind}**: {len(ind_signals)} 条，均分 {avg_score:.1f}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # === 逐条深度分析 ===
    signal_num = 0
    for industry in sorted(by_industry.keys()):
        ind_signals = by_industry[industry]
        lines.append(f"## {industry} ({len(ind_signals)} 条)")
        lines.append("")

        for signal in ind_signals:
            signal_num += 1
            title = signal.get("title", "")
            stype = signal.get("signal_type_name", "")
            score = signal.get("score", 0)
            snippet = signal.get("snippet", "")
            url = signal.get("url", "")
            source_name = signal.get("source_name", "")
            metadata = signal.get("metadata", {})

            lines.append(f"### #{signal_num} [{score:.1f}分] [{stype}] {title}")
            lines.append("")
            lines.append(f"**来源**: {source_name} | **链接**: {url}")
            if snippet:
                lines.append(f"**摘要**: {snippet}")
            lines.append("")

            # 关键词
            kw = _extract_keywords(title, snippet)
            lines.append(f"**关键词**: {' · '.join(kw) if kw else '(未提取到)'}")
            lines.append("")

            # 交叉验证
            lines.append("#### 多源交叉验证")
            lines.append("")
            try:
                refs = _cross_validate(signal)
                if refs:
                    for j, ref in enumerate(refs[:5], 1):
                        lines.append(f"{j}. [{ref['title'][:80]}]({ref['url']})")
                        if ref.get("snippet"):
                            lines.append(f"   > {ref['snippet'][:150]}")
                    lines.append("")
                else:
                    lines.append("*(DDG搜索未返回结果)*")
                    lines.append("")
            except Exception as e:
                lines.append(f"*(搜索异常: {e})*")
                lines.append("")

            # 元数据
            if metadata:
                lines.append("#### 原始数据")
                lines.append("")
                meta_clean = {k: v for k, v in metadata.items() if v and v != 0}
                if meta_clean:
                    for k, v in list(meta_clean.items())[:5]:
                        lines.append(f"- **{k}**: {v}")
                lines.append("")

            # 分析框架（供 AI 填充）
            lines.append("#### 分析框架")
            lines.append("")
            lines.append("| 维度 | 分析 |")
            lines.append("|------|------|")
            lines.append("| **事实确认** | 待验证：该信号是否可靠？多源交叉验证结果？ |")
            lines.append("| **商业解读** | 待分析：为什么重要？背后的商业逻辑？ |")
            lines.append("| **机会评估** | 待评估：个人/小团队有什么机会？市场规模？入场时机？ |")
            lines.append("| **行动建议** | 待生成：具体可做什么？第一步是什么？需要什么资源？ |")
            lines.append("| **风险提示** | 待评估：不确定因素？可能的风险？ |")
            lines.append("| **持续追踪** | 待定义：需关注什么指标来验证趋势？ |")
            lines.append("")

            # 搜索提示
            lines.append("<details>")
            lines.append("<summary>搜索提示词（点击展开）</summary>")
            lines.append("")
            for q_idx, q in enumerate(kw[:4], 1):
                lines.append(f"- 搜索 {q_idx}: `{title[:40]} {q} 2026`")
            lines.append(f"- 搜索 {q_idx+1}: `{title[:40]} 趋势 分析`")
            lines.append(f"- 搜索 {q_idx+2}: `{title[:40]} 市场规模 机会`")
            lines.append("")
            lines.append("</details>")
            lines.append("")
            lines.append("---")
            lines.append("")

    # === 综合行动清单 ===
    lines.append("## 综合行动清单")
    lines.append("")
    lines.append("| 优先级 | 信号 | 建议行动 | 时间框架 |")
    lines.append("|--------|------|----------|----------|")
    for i, s in enumerate(selected_signals, 1):
        score = s.get("score", 0)
        pri = "🔴 高" if score >= 8 else ("🟡 中" if score >= 6 else "🟢 低")
        lines.append(f"| {pri} | #{i} {s.get('title', '')[:40]} | 待填充 | - |")
    lines.append("")

    # === 附录 ===
    lines.append("## 附录: 信号索引")
    lines.append("")
    lines.append("| # | 评分 | 行业 | 类型 | 标题 |")
    lines.append("|---|------|------|------|------|")
    for i, s in enumerate(selected_signals, 1):
        lines.append(
            f"| {i} | {s.get('score', 0):.1f} | {s.get('industry_name', '')} | "
            f"{s.get('signal_type_name', '')} | {s.get('title', '')[:50]} |"
        )
    lines.append("")

    report_md = "\n".join(lines)

    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / f"report_{date_str}.md"
    report_path.write_text(report_md, encoding="utf-8")

    print(f"[日报] 已生成: {report_path}")
    print(f"[提示] 日报包含分析框架，可用 Claude Code 填充分析内容")
    return str(report_path)


# === 交互式分析（在 Claude Code 会话中使用）===

def generate_analysis_prompt(signals, date_str=None):
    """生成供 Claude Code 会话使用的分析 prompt"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    by_industry = defaultdict(list)
    for s in signals:
        by_industry[s.get("industry_name", "其他")].append(s)

    prompt_lines = [
        f"请对以下 {len(signals)} 条行业信号进行深度分析，生成日报。",
        f"",
        f"对每条信号，用 MCP 搜索工具（ddg + bing）做交叉验证后，按以下6个维度输出分析：",
        f"1. 事实确认：信号是否可靠？多源验证结果？",
        f"2. 商业解读：为什么重要？背后的商业逻辑？",
        f"3. 机会评估：个人/小团队有什么机会？市场规模？入场时机？",
        f"4. 行动建议：具体可做什么？第一步？需要什么资源？",
        f"5. 风险提示：不确定因素？可能风险？",
        f"6. 持续追踪：接下来需要关注什么指标？",
        f"",
        f"---",
        f"",
    ]

    for i, s in enumerate(signals, 1):
        prompt_lines.append(
            f"### 信号{i}: [{s.get('score', 0):.1f}分] [{s.get('signal_type_name', '')}] "
            f"{s.get('title', '')}"
        )
        prompt_lines.append(f"行业: {s.get('industry_name', '')} | 来源: {s.get('source_name', '')}")
        prompt_lines.append(f"链接: {s.get('url', '')}")
        if s.get('snippet'):
            prompt_lines.append(f"摘要: {s.get('snippet', '')}")
        prompt_lines.append("")

    prompt_lines.append("---")
    prompt_lines.append("请将分析结果写入 D:/claude产出/industry-radar/reports/report_{date_str}.md")

    return "\n".join(prompt_lines)


if __name__ == "__main__":
    test_signals = [
        {"title": "DeepSeek开源新模型性能直逼GPT-5，API价格骤降80%",
         "industry_name": "AI/大模型", "signal_type_name": "技术端", "score": 9.2,
         "snippet": "API价格骤降80%", "url": "https://example.com/1",
         "source_name": "GitHub Trending", "metadata": {"stars": 5000}},
        {"title": "Boss直聘AI岗位同比+150%，大模型工程师月薪中位数45K",
         "industry_name": "AI/大模型", "signal_type_name": "需求端", "score": 8.5,
         "snippet": "AI岗位暴增", "url": "https://example.com/2",
         "source_name": "Boss直聘", "metadata": {"job_count": 5000}},
        {"title": "东南亚跨境电商新政策出台，中国卖家注册量单月暴增300%",
         "industry_name": "出海/跨境", "signal_type_name": "机会端", "score": 8.8,
         "snippet": "跨境电商新政策", "url": "https://example.com/3",
         "source_name": "36氪", "metadata": {}},
    ]
    path = analyze_signals(test_signals, "2026-05-28")
    print(f"\n日报: {path}")
