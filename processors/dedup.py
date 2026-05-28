"""信号去重：基于标题相似度"""

import re
from difflib import SequenceMatcher


def _normalize(text):
    """标准化文本用于相似度比较"""
    t = text.lower().strip()
    # 去除标点符号
    t = re.sub(r'[^\w\s]', '', t)
    # 去除多余空格
    t = re.sub(r'\s+', ' ', t)
    return t


def _similarity(a, b):
    """计算两段文本的相似度 (0-1)"""
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _same_url(signal, seen_urls):
    """检查URL是否已存在"""
    url = signal.get("url", "").strip().rstrip("/")
    if not url:
        return False
    for seen in seen_urls:
        if seen.rstrip("/") == url:
            return True
    return False


def deduplicate(signals, title_threshold=0.82):
    """
    去重策略：
    1. 完全相同的URL → 去重
    2. 标题相似度 > threshold → 去重（保留评分更高的）
    3. 不同来源的同一事件 → 保留（后续交叉验证需要）

    返回去重后的信号列表
    """
    if not signals:
        return []

    # 预处理：确保每个信号是dict
    processed = []
    for s in signals:
        if hasattr(s, "to_dict"):
            d = s.to_dict()
        elif hasattr(s, "__dict__") and "title" in s.__dict__:
            d = {"title": s.title, "url": getattr(s, "url", ""), **{k: v for k, v in s.__dict__.items()}}
        elif isinstance(s, dict):
            d = s
        else:
            continue
        processed.append(d)

    if not processed:
        return []

    # 按评分降序排列（有score的优先保留）
    processed.sort(key=lambda x: float(x.get("score", x.get("metadata", {}).get("score", 0)) or 0), reverse=True)

    seen_urls = set()
    result = []

    for signal in processed:
        url = signal.get("url", "").strip()
        title = signal.get("title", "")

        if not title:
            continue

        # 完全相同的URL跳过
        if url and url in seen_urls:
            continue

        # 标题相似度检查
        is_dup = False
        norm_title = _normalize(title)
        if len(norm_title) < 10:  # 太短的标题不做相似度判断
            pass
        else:
            for existing in result:
                existing_title = existing.get("title", "")
                if len(_normalize(existing_title)) < 10:
                    continue
                if _similarity(title, existing_title) > title_threshold:
                    is_dup = True
                    break

        if not is_dup:
            if url:
                seen_urls.add(url)
            result.append(signal)

    return result


if __name__ == "__main__":
    # 简单测试
    test = [
        {"title": "OpenAI发布GPT-5新模型", "url": "https://example.com/1"},
        {"title": "OpenAI发布GPT-5新模型！", "url": "https://example.com/2"},  # 相似标题
        {"title": "Google推出新搜索功能", "url": "https://example.com/3"},
        {"title": "OpenAI发布GPT-5新模型", "url": "https://example.com/1"},  # 重复URL
    ]
    result = deduplicate(test)
    print(f"去重前: {len(test)}, 去重后: {len(result)}")
    for r in result:
        print(f"  - {r['title']}")
