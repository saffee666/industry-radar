"""信号优先级打分算法 — v2: 正态分布，3-9区间有效区分"""

import re
import math
from datetime import datetime, timedelta


def score_signals(signals):
    """
    综合打分 (1-10)，目标是让分数分布在 3-9 区间：
    - 时效性 (0-1.5)：近6h = +1.5, 近24h = +0.8, 近72h = +0.3
    - 信号强度 (0-3.0)：基于实际量化指标，log缩放避免极端值
    - 可操作性 (0-1.5)：信号类型 + 具体可操作指标
    - 来源质量 (-0.5~+1.0)：信源权威度微调
    - 标题质量 (-0.5~0)：太短/太长惩罚

    分数含义：9-10=必须关注, 7-8=重要, 5-6=可关注, 3-4=低价值
    """

    # 信源质量加分（微调，不再主导分数）
    source_bonus = {
        "job_markets": 0.8,
        "search_trends": 0.6,
        "policy_media": 0.5,
        "tech_communities": 0.4,
        "freelance_markets": 0.4,
        "chinese_platforms": 0.2,
    }

    # 信号类型行动力加分
    type_bonus = {
        "opportunity": 1.0,
        "demand": 0.7,
        "policy": 0.5,
        "market": 0.4,
        "tech": 0.3,
        "competitive": 0.2,
    }

    now = datetime.now()

    for signal in signals:
        # 基础分 4.0（中性起点，大多数信号会在此基础上下浮动）
        score = 4.0
        metadata = signal.get("metadata", {})

        # === 1. 时效性 (0 ~ +1.5) ===
        timestamp = signal.get("timestamp", "")
        if timestamp:
            try:
                t = datetime.fromisoformat(timestamp)
                hours_ago = (now - t).total_seconds() / 3600
                if hours_ago < 6:
                    score += 1.5
                elif hours_ago < 24:
                    score += 0.8
                elif hours_ago < 72:
                    score += 0.3
            except (ValueError, TypeError):
                pass

        # === 2. 信号强度 (0 ~ +3.0) — log缩放 ===
        strength = 0.0

        # 热度值（微博/百度/抖音 etc.）
        hot_score = metadata.get("hot_score", metadata.get("hot_value", 0))
        if isinstance(hot_score, str):
            try:
                hot_score = float(re.sub(r'[^\d.]', '', str(hot_score)))
            except (ValueError, TypeError):
                hot_score = 0
        if isinstance(hot_score, (int, float)) and hot_score > 0:
            strength += math.log10(max(hot_score, 1)) * 0.4  # 1000→1.2, 10000→1.6, 100000→2.0

        # HN/Reddit score
        score_val = metadata.get("score", 0)
        if isinstance(score_val, str):
            try:
                score_val = float(score_val)
            except (ValueError, TypeError):
                score_val = 0
        if isinstance(score_val, (int, float)) and score_val > 0:
            strength += math.log10(max(score_val, 1)) * 0.3

        # 招聘岗位数
        job_count = metadata.get("job_count", 0)
        if isinstance(job_count, (int, float)) and job_count > 0:
            strength += math.log10(max(job_count, 1)) * 0.5

        # GitHub stars
        stars = metadata.get("stars", 0)
        if isinstance(stars, (int, float)) and stars > 0:
            strength += math.log10(max(stars, 1)) * 0.3

        # PH votes / comments
        votes = metadata.get("votes", metadata.get("comments", 0))
        if isinstance(votes, (int, float)) and votes > 0:
            strength += math.log10(max(votes, 1)) * 0.25

        score += min(strength, 3.0)  # cap at 3.0

        # === 3. 可操作性 (0 ~ +1.5) ===
        stype = signal.get("signal_type", "market")
        score += type_bonus.get(stype, 0.2)

        # 有具体数据增强可操作性
        if metadata.get("job_count") or metadata.get("price"):
            score += 0.3
        if metadata.get("url") and signal.get("source") in ("job_markets", "freelance_markets"):
            score += 0.3

        # === 4. 来源质量 (-0.5 ~ +0.8) ===
        category = signal.get("category", "")
        score += source_bonus.get(category, 0.0)

        # === 5. 标题质量 (-0.5 ~ 0) ===
        title = signal.get("title", "")
        if len(title) <= 5:
            score -= 0.5
        elif len(title) > 100:
            score -= 0.3

        # === 6. 去重标题惩罚（纯数字/纯英文短标题）===
        if re.match(r'^[\d\.\s]+$', title):
            score -= 1.0

        # 限制在 1.0-10.0
        score = max(1.0, min(10.0, score))
        signal["score"] = round(score, 1)

    signals.sort(key=lambda x: x.get("score", 0), reverse=True)
    return signals


if __name__ == "__main__":
    test = [
        {"title": "AI岗位暴增", "timestamp": datetime.now().isoformat(), "metadata": {"job_count": 5000}, "signal_type": "demand", "category": "job_markets"},
        {"title": "某开源工具发布", "timestamp": datetime.now().isoformat(), "metadata": {}, "signal_type": "tech", "category": "tech_communities"},
    ]
    result = score_signals(test)
    for s in result:
        print(f"  [{s['score']}] {s['title']}")
