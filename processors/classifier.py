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
    for pattern in keywords_list:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        except re.error:
            if pattern.lower() in text:
                return True
    return False


def _count_keyword_matches(text, keywords_list):
    """计数匹配到的关键词模式数"""
    count = 0
    for pattern in keywords_list:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                count += 1
        except re.error:
            if pattern.lower() in text:
                count += 1
    return count


# 各行业的高优先级单字/短词 — 精确子串匹配，不依赖正则
STRONG_INDICATORS = {
    "ai": ["AI", "大模型", "GPT", "Claude", "DeepSeek", "智能", "神经网络", "机器人"],
    "web3": ["比特币", "以太坊", "区块链", "NFT", "Web3", "crypto", "DeFi"],
    "ecommerce": ["电商", "淘宝", "拼多多", "京东", "直播带货", "跨境电商"],
    "saas": ["SaaS", "开源", "程序员", "开发者", "API", "云原生", "Kubernetes"],
    "newenergy": ["新能源", "光伏", "电动车", "特斯拉", "比亚迪", "碳中和", "电池"],
    "fintech": ["A股", "股票", "基金", "IPO", "上市", "央行", "利率", "支付"],
    "content": ["短剧", "抖音", "短视频", "网红", "直播", "UP主", "剧本"],
    "consumer": ["奶茶", "咖啡", "瑞幸", "喜茶", "美妆", "宠物", "盲盒"],
    "health": ["医保", "创新药", "医疗器械", "养老", "医美", "减肥药"],
    "gaming": ["游戏", "电竞", "手游", "原神", "米哈游", "Unity"],
    "overseas": ["出海", "跨境", "TikTok", "东南亚", "外贸"],
    "education": ["教育", "培训", "考研", "高考", "留学", "网课"],
}


def classify_industry(signal):
    """对单条信号进行行业分类，返回行业ID"""
    rules = _load_rules()
    industries = rules["industries"]

    title = signal.get("title", "")
    snippet = signal.get("snippet", "")
    raw_text = signal.get("raw_text", "")
    metadata = signal.get("metadata", {})
    meta_text = " ".join(str(v) for v in metadata.values() if isinstance(v, str))
    text = f"{title} {snippet} {raw_text} {meta_text}"
    text_lower = text.lower()

    scores = {}
    for ind_id, ind_config in industries.items():
        if ind_id == "other":
            continue
        cn_kw = ind_config.get("keywords_cn", [])
        en_kw = ind_config.get("keywords_en", [])
        regex_count = _count_keyword_matches(text_lower, cn_kw + en_kw)

        # 强指示词加分（每个匹配 +3，远高于普通正则匹配的 +1）
        strong_count = 0
        for indicator in STRONG_INDICATORS.get(ind_id, []):
            if indicator.lower() in text_lower:
                strong_count += 1

        total = regex_count + strong_count * 3
        if total > 0:
            scores[ind_id] = total

    if scores:
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
