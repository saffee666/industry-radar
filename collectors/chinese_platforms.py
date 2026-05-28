"""中文平台采集器: 知乎热榜, B站热门, 即刻, 少数派"""

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
    return [s for s in config["sources"]["chinese_platforms"] if s.get("enabled")]


def _zhihu_hot():
    """知乎热榜 — 用API"""
    signals = []
    try:
        resp = requests.get(
            "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total",
            headers={**HEADERS, "Referer": "https://www.zhihu.com/hot"},
            params={"limit": 30, "desktop": "true"},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("data", []):
                target = item.get("target", {})
                title = target.get("title", "")
                url = target.get("url", f"https://www.zhihu.com/question/{target.get('id', '')}")
                excerpt = target.get("excerpt", "")[:100]
                signals.append(make_signal(
                    title=title,
                    url=url,
                    source="zhihu_hot",
                    source_name="知乎热榜",
                    category="chinese_platforms",
                    language="zh",
                    snippet=excerpt,
                    raw_text=f"{title} {excerpt}",
                    metadata={
                        "hot_value": item.get("detail_text", ""),
                        "metrics": item.get("target", {}).get("metrics_area", {}).get("text", "")
                    }
                ))
    except Exception as e:
        print(f"   知乎API异常: {e}")
    return signals


def _bilibili_hot():
    """B站热门 — 用API"""
    signals = []
    try:
        resp = requests.get(
            "https://api.bilibili.com/x/web-interface/popular",
            headers={**HEADERS, "Referer": "https://www.bilibili.com/"},
            params={"ps": 20, "pn": 1},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            for item in data.get("list", [])[:20]:
                title = item.get("title", "")
                desc = item.get("desc", "")[:100]
                signals.append(make_signal(
                    title=title,
                    url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                    source="bilibili_hot",
                    source_name="B站热门",
                    category="chinese_platforms",
                    language="zh",
                    snippet=desc,
                    raw_text=f"{title} {desc} {item.get('owner', {}).get('name', '')}",
                    metadata={
                        "views": item.get("stat", {}).get("view", 0),
                        "danmaku": item.get("stat", {}).get("danmaku", 0),
                        "author": item.get("owner", {}).get("name", "")
                    }
                ))
    except Exception as e:
        print(f"   B站API异常: {e}")
    return signals


def _sspai():
    """少数派 — 新版API: /api/v1/article/index/page/get"""
    import time
    signals = []
    try:
        ts = int(time.time() * 1000)
        resp = requests.get(
            f"https://sspai.com/api/v1/article/index/page/get?limit=20&offset=0&created_at={ts}&view=second",
            headers={**HEADERS, "Referer": "https://sspai.com/"},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", data) if isinstance(data, dict) else data
            if isinstance(items, list):
                for item in items[:20]:
                    title = item.get("title", "")
                    item_id = item.get("id", "")
                    signals.append(make_signal(
                        title=title,
                        url=f"https://sspai.com/post/{item_id}",
                        source="sspai",
                        source_name="少数派",
                        category="chinese_platforms",
                        language="zh",
                        snippet=item.get("summary", "")[:120],
                        raw_text=f"{title} {item.get('summary', '')}",
                        metadata={
                            "author": item.get("author", {}).get("nickname", ""),
                            "likes": item.get("like_count", 0),
                            "comments": item.get("comment_count", 0),
                        }
                    ))
    except Exception as e:
        print(f"   少数派异常: {e}")
    return signals


def _jike():
    """即刻 — web版API"""
    signals = []
    try:
        # 即刻 Web API (无需登录的公开接口)
        resp = requests.post(
            "https://web-api.okjike.com/api/graphql",
            headers={**HEADERS, "Content-Type": "application/json"},
            json={
                "operationName": "FollowingUpdates",
                "query": "query FollowingUpdates{followingUpdates(first:20,after:\"\"){edges{node{id content pictures{thumbUrl}topic{content}}}}}"  # noqa
            },
            timeout=15
        )
        # 即刻需要token，公开API不可用则跳过
    except Exception:
        pass
    return signals


def collect_chinese_platforms():
    """采集所有中文平台信号源"""
    import yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    sources = [s for s in config["sources"]["chinese_platforms"] if s.get("enabled")]

    all_signals = []

    collectors = {
        "zhihu_hot": _zhihu_hot,
        "bilibili_hot": _bilibili_hot,
        "sspai": _sspai,
        "jike_product": _jike,
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
    signals = collect_chinese_platforms()
    for s in signals:
        print(f"  [{s.source_name}] {s.title[:60]}")
