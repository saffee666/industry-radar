"""信号优先级打分算法"""

import re
from datetime import datetime, timedelta


def score_signals(signals):
    """
    综合打分 (1-10)：
    - 时效性 (0-3分)：发布时间越近越好
    - 信号强度 (0-3分)：提及量/热度/互动量
    - 可操作性 (0-2分)：能否转化为具体行动
    - 多样性加权 (0-2分)：信息源权威度 + 行业覆盖
    """
    now = datetime.now()

    # 信源权重
    source_weights = {
        "tech_communities": 1.5,
        "chinese_platforms": 1.3,
        "search_trends": 1.8,   # 搜索趋势信号最强
        "freelance_markets": 1.6,
        "job_markets": 1.7,     # 招聘数据高价值
        "policy_media": 1.4,
    }

    # 信号类型行动力加分
    type_action_bonus = {
        "opportunity": 1.0,  # 机会信号最大加分
        "demand": 0.6,
        "market": 0.3,
        "tech": 0.2,
        "competitive": 0.1,
        "policy": 0.4,
    }

    for signal in signals:
        # 基础分 3.0，留出 0-7 的加分空间
        score = 3.0
        metadata = signal.get("metadata", {})

        # 1. 时效性 (0-2.5)
        timestamp = signal.get("timestamp", "")
        if timestamp:
            try:
                t = datetime.fromisoformat(timestamp)
                hours_ago = (now - t).total_seconds() / 3600
                if hours_ago < 6:
                    score += 2.5
                elif hours_ago < 24:
                    score += 1.5
                elif hours_ago < 72:
                    score += 0.5
            except (ValueError, TypeError):
                pass  # 无时间不加分

        # 2. 信号强度 (0-2.5) — 基于元数据中的量化指标
        hot_score = metadata.get("hot_score", metadata.get("hot_value", 0))
        if isinstance(hot_score, str):
            try:
                hot_score = float(re.sub(r'[^\d.]', '', str(hot_score)))
            except (ValueError, TypeError):
                hot_score = 0

        score_val = metadata.get("score", 0)
        if isinstance(score_val, str):
            try:
                score_val = float(score_val)
            except (ValueError, TypeError):
                score_val = 0

        if isinstance(hot_score, (int, float)) and hot_score > 500000:
            score += 2.5
        elif isinstance(hot_score, (int, float)) and hot_score > 100000:
            score += 2.0
        elif isinstance(hot_score, (int, float)) and hot_score > 10000:
            score += 1.0
        elif isinstance(score_val, (int, float)) and score_val > 50:
            score += 1.5
        elif isinstance(score_val, (int, float)) and score_val > 10:
            score += 0.5

        # 招聘岗位数量 → 强度加分
        job_count = metadata.get("job_count", 0)
        if isinstance(job_count, (int, float)) and job_count > 5000:
            score += 2.5
        elif isinstance(job_count, (int, float)) and job_count > 1000:
            score += 2.0
        elif isinstance(job_count, (int, float)) and job_count > 100:
            score += 1.0

        # forks/stars (GitHub)
        stars = metadata.get("stars", 0)
        if isinstance(stars, (int, float)) and stars > 10000:
            score += 1.5
        elif isinstance(stars, (int, float)) and stars > 1000:
            score += 0.5

        # votes (Product Hunt)
        votes = metadata.get("votes", 0)
        if isinstance(votes, (int, float)) and votes > 500:
            score += 1.5
        elif isinstance(votes, (int, float)) and votes > 100:
            score += 0.5

        # 3. 可操作性 (0-1.5)
        stype = signal.get("signal_type", "")
        score += type_action_bonus.get(stype, 0)

        if stype == "demand" and metadata.get("job_count", 0):
            score += 0.5
        if stype == "opportunity" and (metadata.get("price") or metadata.get("bids")):
            score += 0.5

        # 4. 来源权威度调整 (-0.5 ~ +1.0)
        category = signal.get("category", "")
        src_weight = source_weights.get(category, 1.0)
        if src_weight > 1.2:
            score += 1.0
        elif src_weight > 1.0:
            score += 0.5

        # 标题长度惩罚：太短(≤5字)或太长(≥80字)扣分
        title = signal.get("title", "")
        if len(title) <= 5:
            score -= 0.5
        elif len(title) >= 80:
            score -= 0.3

        # 限制在 1-10 范围
        score = max(1.0, min(10.0, score))
        signal["score"] = round(score, 1)

    # 按分数降序排列
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
