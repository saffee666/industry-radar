"""交易/接单平台采集器: 猪八戒, Upwork"""

import re
import requests
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
    return [s for s in config["sources"]["freelance_markets"] if s.get("enabled")]


def _zbj():
    """猪八戒需求大厅 — 需登录cookie"""
    from .cookie_loader import apply_cookies
    session = requests.Session()
    cookie_count = apply_cookies(session, "zbj_demand")
    if not cookie_count:
        print("   猪八戒: 缺少cookie，跳过（请在浏览器登录后导出cookie）")
        return []

    signals = []
    try:
        resp = session.get(
            "https://task.zbj.com/api/task/search",
            params={"keyword": "", "page": 1, "pageSize": 20, "sort": "publishTime desc"},
            headers={**HEADERS, "Referer": "https://task.zbj.com/"},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("data", {}).get("list", data.get("data", []))
            if isinstance(items, list):
                for item in items[:20]:
                    title = item.get("title", item.get("name", ""))
                    signals.append(make_signal(
                        title=title,
                        url=item.get("url", f"https://task.zbj.com/{item.get('id', '')}"),
                        source="zbj_demand",
                        source_name="猪八戒",
                        category="freelance_markets",
                        language="zh",
                        snippet=item.get("description", item.get("desc", ""))[:120],
                        raw_text=f"{title} {item.get('description', item.get('desc', ''))}",
                        metadata={
                            "price": item.get("price", item.get("budget", "")),
                            "category": item.get("categoryName", item.get("category", "")),
                            "bids": item.get("bidCount", item.get("bids", 0)),
                        }
                    ))
    except Exception as e:
        # Fallback: 抓HTML（也带cookie）
        try:
            html = session.get("https://task.zbj.com/", headers=HEADERS, timeout=20).text
            items = re.findall(r'class="[^"]*task-title[^"]*"[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', html, re.DOTALL)
            for url, title in items[:15]:
                signals.append(make_signal(
                    title=title.strip(),
                    url="https://task.zbj.com" + url if url.startswith("/") else url,
                    source="zbj_demand", source_name="猪八戒", category="freelance_markets",
                    language="zh", snippet=title.strip()
                ))
        except Exception as e2:
            print(f"   猪八戒异常: {e2}")
    return signals


def _upwork_skills():
    """Upwork Trending Skills"""
    signals = []
    try:
        html = requests.get(
            "https://www.upwork.com/resources/trending-skills",
            headers={**HEADERS, "Accept-Language": "en-US,en;q=0.9"},
            timeout=15
        ).text

        # 提取技能标题和描述
        sections = re.findall(r'<h3[^>]*>([^<]+)</h3>\s*<p[^>]*>([^<]+)</p>', html)
        for title, desc in sections[:20]:
            signals.append(make_signal(
                title=f"Trending Skill: {title.strip()}",
                url="https://www.upwork.com/resources/trending-skills",
                source="upwork_skills",
                source_name="Upwork Skills",
                category="freelance_markets",
                language="en",
                snippet=desc.strip()[:120],
                raw_text=f"{title.strip()} {desc.strip()}",
            ))

        # 也抓具体技能文章链接
        articles = re.findall(r'<a[^>]*href="(/resources/[^"]*skill[^"]*)"[^>]*>([^<]+)</a>', html)
        for url, title in articles[:10]:
            signals.append(make_signal(
                title=title.strip(),
                url="https://www.upwork.com" + url,
                source="upwork_skills", source_name="Upwork Skills",
                category="freelance_markets", language="en", snippet=title.strip()
            ))
    except Exception as e:
        print(f"   Upwork异常: {e}")
    return signals


def collect_freelance_markets():
    """采集所有交易/接单平台信号源"""
    import yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    sources = [s for s in config["sources"]["freelance_markets"] if s.get("enabled")]

    all_signals = []

    collectors = {
        "zbj_demand": _zbj,
        "upwork_skills": _upwork_skills,
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
    signals = collect_freelance_markets()
    for s in signals:
        print(f"  [{s.source_name}] {s.title[:60]}")
