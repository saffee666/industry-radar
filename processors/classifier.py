"""信号分类器：行业分类 + 信号类型分类"""

import re
import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "industries.yaml"


def _load_rules():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _match_keywords(text, keywords_list):
    """检查文本是否匹配关键词列表中的任一正则"""
    text_lower = text.lower()
    for pattern in keywords_list:
        try:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        except re.error:
            if pattern.lower() in text_lower:
                return True
    return False


def classify_industry(signal):
    """对单条信号进行行业分类，返回行业ID"""
    rules = _load_rules()
    industries = rules["industries"]

    # 合并所有文本用于匹配（含metadata中的职位/公司信息）
    title = signal.get("title", "")
    snippet = signal.get("snippet", "")
    raw_text = signal.get("raw_text", "")
    metadata = signal.get("metadata", {})
    meta_text = " ".join(str(v) for v in metadata.values() if isinstance(v, str))
    text = f"{title} {snippet} {raw_text} {meta_text}"

    # 按关键词匹配
    scores = {}
    for ind_id, ind_config in industries.items():
        if ind_id == "other":
            continue
        cn_match = _match_keywords(text, ind_config.get("keywords_cn", []))
        en_match = _match_keywords(text, ind_config.get("keywords_en", []))
        if cn_match or en_match:
            # 计算匹配分数：匹配到的关键词数
            all_kw = ind_config.get("keywords_cn", []) + ind_config.get("keywords_en", [])
            match_count = sum(1 for kw in all_kw if re.search(kw, text.lower(), re.IGNORECASE))
            scores[ind_id] = match_count

    if scores:
        # 返回得分最高的行业
        best = max(scores, key=scores.get)
        return best

    return "other"


def classify_signal_type(signal):
    """对单条信号进行类型分类，返回信号类型ID"""
    rules = _load_rules()
    stypes = rules["signal_types"]

    title = signal.get("title", "")
    snippet = signal.get("snippet", "")
    raw_text = signal.get("raw_text", "")
    metadata = signal.get("metadata", {})
    meta_text = " ".join(str(v) for v in metadata.values() if isinstance(v, str))
    text = f"{title} {snippet} {raw_text} {meta_text}"

    scores = {}
    for stype_id, stype_config in stypes.items():
        if _match_keywords(text, stype_config.get("keywords", [])):
            keywords = stype_config["keywords"]
            match_count = sum(1 for kw in keywords if re.search(kw, text.lower(), re.IGNORECASE))
            scores[stype_id] = match_count

    if scores:
        best = max(scores, key=scores.get)
        return best

    return "market"  # 默认归为市场端


def classify_signals(signals):
    """对信号列表进行行业+类型分类，原地修改并返回"""
    rules = _load_rules()
    ind_names = {k: v["name"] for k, v in rules["industries"].items()}
    type_names = {k: v["name"] for k, v in rules["signal_types"].items()}

    for signal in signals:
        ind_id = classify_industry(signal)
        stype_id = classify_signal_type(signal)

        signal["industry"] = ind_id
        signal["industry_name"] = ind_names.get(ind_id, "其他")
        signal["signal_type"] = stype_id
        signal["signal_type_name"] = type_names.get(stype_id, "市场端")

    return signals


if __name__ == "__main__":
    test_signals = [
        {"title": "DeepSeek发布新模型，性能逼近GPT-5，API价格大幅下降", "snippet": "AI大模型价格战", "raw_text": ""},
        {"title": "东南亚跨境电商政策放宽，卖家数量激增", "snippet": "出海电商新机会", "raw_text": ""},
        {"title": "Boss直聘上AI岗位数量翻倍，薪资上涨30%", "snippet": "AI人才紧缺", "raw_text": ""},
        {"title": "国务院发布新能源补贴新政", "snippet": "光伏补贴加码", "raw_text": ""},
        {"title": "某网红奶茶品牌获亿元融资", "snippet": "消费赛道回暖", "raw_text": ""},
    ]

    result = classify_signals(test_signals)
    for s in result:
        print(f"  [{s['industry_name']}][{s['signal_type_name']}] {s['title'][:50]}")
