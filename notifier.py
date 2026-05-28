"""推送通知：企业微信机器人 webhook"""

import requests
from datetime import datetime
from pathlib import Path
from collections import Counter

WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=bbad7b83-e807-4d3f-8993-1f63b0bb3f31"


def send_markdown(content):
    """发送 markdown 消息到企业微信群机器人"""
    resp = requests.post(
        WEBHOOK_URL,
        json={"msgtype": "markdown", "markdown": {"content": content}},
        timeout=15,
    )
    result = resp.json()
    ok = result.get("errcode") == 0
    if not ok:
        print(f"   [推送失败] {result.get('errmsg', '')}")
    return ok


def send_text(content, mentioned_list=None):
    """发送纯文本消息"""
    body = {"msgtype": "text", "text": {"content": content}}
    if mentioned_list:
        body["text"]["mentioned_list"] = mentioned_list
    resp = requests.post(WEBHOOK_URL, json=body, timeout=15)
    result = resp.json()
    return result.get("errcode") == 0


def push_morning_brief(scored_signals, date_str=None):
    """推送晨报摘要到微信"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    total = len(scored_signals)
    if total == 0:
        send_text(f"行业雷达 {date_str}：今日未采集到信号")
        return

    # 分数分布
    high = [s for s in scored_signals if s.get("score", 0) >= 8.0]
    mid = [s for s in scored_signals if 6.0 <= s.get("score", 0) < 8.0]
    low = [s for s in scored_signals if s.get("score", 0) < 6.0]

    # 行业分布
    industries = Counter(s.get("industry_name", "其他") for s in scored_signals)
    top_inds = industries.most_common(5)

    # 类型分布
    types = Counter(s.get("signal_type_name", "") for s in scored_signals)

    # 构建 markdown 消息（企业微信限制 4096 字符）
    lines = [
        f"# 行业雷达晨报 — {date_str}",
        "",
        f"**今日信号**: {total} 条",
        f"**高优 (≥8)**: <font color=\"warning\">{len(high)}</font> 条 | **中优**: {len(mid)} 条 | **普通**: {len(low)} 条",
        "",
        "**行业TOP5**:",
    ]
    for ind, cnt in top_inds:
        lines.append(f"- {ind}: {cnt}条")
    lines.append("")

    type_summary = " · ".join(f"{t}({c})" for t, c in types.most_common(4))
    lines.append(f"**信号类型**: {type_summary}")
    lines.append("")

    # 高优信号列表（最多8条）
    if high:
        lines.append("---")
        lines.append("")
        lines.append("## 高优信号")
        lines.append("")
        for i, s in enumerate(high[:8], 1):
            title = s.get("title", "")[:50]
            score = s.get("score", 0)
            ind = s.get("industry_name", "")
            stype = s.get("signal_type_name", "")
            lines.append(f"{i}. <font color=\"info\">[{score:.1f}]</font> [{ind}] [{stype}] {title}")

    lines.append("")
    brief_path = f"D:/claude产出/industry-radar/briefs/brief_{date_str}.md"
    lines.append(f"[查看完整晨报](file:///{brief_path.replace(' ', '%20')})")
    lines.append("")
    lines.append(f"> {datetime.now().strftime('%H:%M')} 自动生成 | repo: [industry-radar](https://github.com/saffee666/industry-radar)")

    content = "\n".join(lines)

    # 截断到 4000 字符（企业微信 markdown 限制 4096）
    if len(content) > 4000:
        content = content[:3990] + "\n> ...(内容过长已截断)"

    send_markdown(content)


def push_report_ready(report_path, signal_count, date_str=None):
    """推送深度日报完成通知"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    path = Path(report_path)
    lines = [
        f"# 深度日报已生成 — {date_str}",
        "",
        f"分析了 **{signal_count}** 条信号",
        f"报告路径: `{str(path)}`",
        "",
        "[打开报告](file:///{})".format(str(path).replace(" ", "%20").replace("\\", "/")),
    ]
    send_markdown("\n".join(lines))


if __name__ == "__main__":
    # 测试推送
    test_signals = [
        {"title": "DeepSeek开源新模型API价格骤降80%", "industry_name": "AI/大模型", "signal_type_name": "技术端", "score": 9.2},
        {"title": "Boss直聘AI岗位同比+150%", "industry_name": "AI/大模型", "signal_type_name": "需求端", "score": 8.5},
        {"title": "东南亚电商新政策，卖家暴增300%", "industry_name": "出海/跨境", "signal_type_name": "机会端", "score": 8.8},
        {"title": "某短剧平台日活破千万", "industry_name": "短剧/内容产业", "signal_type_name": "市场端", "score": 7.2},
        {"title": "光伏组件价格触底反弹", "industry_name": "新能源/碳中和", "signal_type_name": "市场端", "score": 6.8},
        {"title": "GitHub万星AI Agent框架", "industry_name": "AI/大模型", "signal_type_name": "技术端", "score": 6.5},
        {"title": "普通信号1", "industry_name": "其他", "signal_type_name": "需求端", "score": 4.5},
        {"title": "普通信号2", "industry_name": "消费品牌", "signal_type_name": "市场端", "score": 5.0},
    ]
    push_morning_brief(test_signals, "2026-05-28")
    print("推送测试完成，检查企业微信")
