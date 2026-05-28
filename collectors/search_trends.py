"""搜索引擎趋势采集器: Google Trends, 百度热搜, 微博热搜"""

import re
import requests
import json
from pathlib import Path
from .base import make_signal

CONFIG_PATH = Path(__file__).parent.parent / "config" / "sources.yaml"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def _load_sources():
    import yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return [s for s in config["sources"]["search_trends"] if s.get("enabled")]


def _google_trends():
    """Google Trends 每日趋势 — RSS feed (免费)"""
    signals = []
    try:
        resp = requests.get(
            "https://trends.google.com/trending/rss?geo=US&hours=24",
            headers=HEADERS,
            timeout=15
        )
        if resp.status_code == 200:
            # 解析 RSS
            items = re.findall(r'<item>.*?<title><!\[CDATA\[([^\]]+)\]\]></title>.*?<link>(.*?)</link>.*?<description>(.*?)</description>', resp.text, re.DOTALL)
            for title, url, desc in items[:25]:
                traffic = re.search(r'([\d,]+[KMB]?)\+.*searches', desc)
                traffic_str = traffic.group(1) if traffic else ""
                signals.append(make_signal(
                    title=f"Trending: {title.strip()}",
                    url=url.strip(),
                    source="google_trends_daily",
                    source_name="Google Trends",
                    category="search_trends",
                    language="en",
                    snippet=desc.strip()[:150],
                    raw_text=f"{title} {desc}",
                    metadata={"traffic": traffic_str}
                ))
    except Exception as e:
        print(f"   Google Trends异常: {e}")
    return signals


def _baidu_hot():
    """百度热搜 — API"""
    signals = []
    try:
        resp = requests.get(
            "https://top.baidu.com/api/board?tab=realtime",
            headers={**HEADERS, "Referer": "https://top.baidu.com/", "Accept-Language": "zh-CN,zh;q=0.9"},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            cards = data.get("data", {}).get("cards", [])
            for card in cards:
                if card.get("component") == "hotList":
                    for item in card.get("content", [])[:30]:
                        word = item.get("word", item.get("query", ""))
                        desc = item.get("desc", "")
                        hot_score = item.get("hotScore", 0)
                        if word:
                            signals.append(make_signal(
                                title=word,
                                url=item.get("appUrl", item.get("url", f"https://www.baidu.com/s?wd={word}")),
                                source="baidu_hot",
                                source_name="百度热搜",
                                category="search_trends",
                                language="zh",
                                snippet=desc[:120] if desc else "",
                                raw_text=f"{word} {desc}",
                                metadata={
                                    "hot_score": hot_score,
                                    "hot_change": item.get("hotChange", ""),
                                    "idx": item.get("index", ""),
                                }
                            ))
                    break
    except Exception as e:
        print(f"   百度热搜异常: {e}")
    return signals


def _weibo_hot():
    """微博热搜"""
    signals = []
    try:
        resp = requests.get(
            "https://weibo.com/ajax/side/hotSearch",
            headers={**HEADERS, "Referer": "https://weibo.com/", "X-Requested-With": "XMLHttpRequest"},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", {}).get("realtime", [])[:20]
            for item in items:
                word = item.get("word", item.get("note", ""))
                if word:
                    signals.append(make_signal(
                        title=word,
                        url=f"https://s.weibo.com/weibo?q={word}",
                        source="weibo_hot",
                        source_name="微博热搜",
                        category="search_trends",
                        language="zh",
                        snippet=item.get("num", ""),
                        raw_text=f"{word} - 热搜",
                        metadata={
                            "rank": item.get("rank", 0),
                            "hot_value": item.get("num", ""),
                            "category": item.get("category", "")
                        }
                    ))
    except Exception as e:
        print(f"   微博热搜异常: {e}")
        # Fallback: 简单接口
        try:
            resp = requests.get(
                "https://tenapi.cn/v2/weibohot",
                headers=HEADERS,
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", [])[:20]:
                    signals.append(make_signal(
                        title=item.get("name", ""),
                        url=f"https://s.weibo.com/weibo?q={item.get('name', '')}",
                        source="weibo_hot", source_name="微博热搜", category="search_trends",
                        language="zh", snippet=f"热度: {item.get('hot', '')}",
                        raw_text=f"{item.get('name', '')} 热搜"
                    ))
        except Exception:
            pass
    return signals


def _xueqiu_hot():
    """雪球热帖 — 需先获取cookie"""
    signals = []
    try:
        sess = requests.Session()
        sess.get("https://xueqiu.com/", headers=HEADERS, timeout=15)
        resp = sess.get(
            "https://xueqiu.com/statuses/hot/listV2.json",
            params={"since_id": -1, "max_id": -1, "size": 15},
            headers={**HEADERS, "Referer": "https://xueqiu.com/"},
            timeout=15
        )
        if resp.status_code != 200:
            return signals
        for item in resp.json().get("items", []):
            os = item.get("original_status", {})
            if not os:
                continue
            title = os.get("title", "") or os.get("description", "")
            if not title:
                title = re.sub(r'<[^>]+>', '', os.get("text", "")).strip()[:80]
            if title and len(title) > 3:
                signals.append(make_signal(
                    title=title[:120],
                    url=f"https://xueqiu.com{item.get('target','')}" if item.get('target') else f"https://xueqiu.com/statuses/{os.get('id','')}",
                    source="xueqiu",
                    source_name="雪球",
                    category="search_trends",
                    language="zh",
                    snippet=re.sub(r'<[^>]+>', '', os.get("text", "")).strip()[:150],
                    raw_text=f"{title}",
                    metadata={
                        "reply_count": os.get("reply_count", 0),
                        "retweet_count": os.get("retweet_count", 0),
                        "user": os.get("user", {}).get("screen_name", "")
                    }
                ))
    except Exception as e:
        print(f"   雪球异常: {e}")
    return signals


def collect_search_trends():
    """采集所有搜索趋势信号源"""
    import yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    sources = [s for s in config["sources"]["search_trends"] if s.get("enabled")]

    all_signals = []

    collectors = {
        "google_trends_daily": _google_trends,
        "baidu_hot": _baidu_hot,
        "weibo_hot": _weibo_hot,
    }

    for src in sources:
        sid = src["id"]
        if sid in collectors:
            try:
                signals = collectors[sid]()
                all_signals.extend(signals)
                print(f"   [{src['name']}] {len(signals)} 条")
            except Exception as e:
                print(f"   [{src['name']}] 失败: {e}")

    return all_signals


if __name__ == "__main__":
    signals = collect_search_trends()
    for s in signals:
        print(f"  [{s.source_name}] {s.title[:60]}")
