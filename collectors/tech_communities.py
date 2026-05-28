"""技术社区采集器: GitHub Trending, Hacker News, Product Hunt, V2EX"""

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
    return [s for s in config["sources"]["tech_communities"] if s.get("enabled")]


def _fetch_html(url):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def _simple_parse(html, selector_rules, base_url=""):
    """用简单正则提取标题+链接，作为无BeautifulSoup时的fallback"""
    results = []
    # 提取所有 <a> 标签中的文本和链接
    links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', html)
    seen_urls = set()
    for url, text in links:
        text = text.strip()
        if not text or len(text) < 5:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        if url.startswith("/"):
            url = base_url.rstrip("/") + url
        elif not url.startswith("http"):
            continue
        results.append({"title": text, "url": url})
    return results[:30]


def _gh_trending():
    """GitHub Trending - search API (免费, 不需要token)"""
    signals = []
    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": "stars:>500", "sort": "stars", "order": "desc", "per_page": 20},
            headers={**HEADERS, "Accept": "application/vnd.github+json"},
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("items", [])[:20]:
                signals.append(make_signal(
                    title=item.get("full_name", ""),
                    url=item.get("html_url", ""),
                    source="github_trending",
                    source_name="GitHub Trending",
                    category="tech_communities",
                    language="en",
                    raw_text=item.get("description", "") or "",
                    snippet=item.get("description", "") or "",
                    metadata={
                        "stars": item.get("stargazers_count", 0),
                        "language": item.get("language", ""),
                        "topics": item.get("topics", []),
                        "forks": item.get("forks_count", 0),
                    }
                ))
            return signals
    except Exception:
        pass

    # Fallback: scrape trending page
    try:
        html = _fetch_html("https://github.com/trending")
        repos = re.findall(r'<a[^>]*href="(/[^/]+/[^/"]+)"[^>]*>', html)
        seen = set()
        for path in repos:
            parts = path.strip("/").split("/")
            if len(parts) == 2 and path not in seen:
                seen.add(path)
                name = "/".join(parts)
                signals.append(make_signal(
                    title=name, url="https://github.com" + path,
                    source="github_trending", source_name="GitHub Trending",
                    category="tech_communities", language="en", snippet=name
                ))
                if len(signals) >= 20:
                    break
    except Exception:
        pass
    return signals


def _hackernews():
    """Hacker News - 官方API (并发请求提速)"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    try:
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15
        )
        ids = resp.json()[:15]
    except Exception as e:
        print(f"   HN API异常: {e}")
        return []

    def fetch_item(item_id):
        try:
            r = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json",
                timeout=8
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    signals = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(fetch_item, i): i for i in ids}
        for f in as_completed(futures, timeout=30):
            item = f.result()
            if item and item.get("title"):
                url = item.get("url", f"https://news.ycombinator.com/item?id={item.get('id', '')}")
                signals.append(make_signal(
                    title=item["title"],
                    url=url,
                    source="hackernews",
                    source_name="Hacker News",
                    category="tech_communities",
                    language="en",
                    snippet=(item.get("text") or "")[:120],
                    metadata={
                        "score": item.get("score", 0),
                        "comments": item.get("descendants", 0)
                    }
                ))
    return signals


def _producthunt():
    """Product Hunt — Atom feed（无需登录）"""
    import xml.etree.ElementTree as ET

    signals = []
    try:
        resp = requests.get(
            "https://www.producthunt.com/feed",
            headers=HEADERS,
            timeout=15
        )
        if resp.status_code != 200:
            print(f"   PH feed: HTTP {resp.status_code}")
            return []

        # Atom XML namespace
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(resp.text)

        for entry in root.findall("atom:entry", ns)[:30]:
            title_el = entry.find("atom:title", ns)
            link_el = entry.find("atom:link", ns)
            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            url = link_el.get("href", "") if link_el is not None else ""
            import html as html_mod
            content_el = entry.find("atom:content", ns)
            raw_html = ""
            if content_el is not None and content_el.text:
                raw_html = html_mod.unescape(content_el.text)
            # Extract first <p> as tagline, skip "Discussion | Link" noise
            tagline_match = re.search(r'<p[^>]*>\s*(.+?)\s*</p>', raw_html, re.DOTALL)
            snippet = tagline_match.group(1).strip()[:120] if tagline_match else ""
            # Remove any remaining HTML tags from snippet
            snippet = re.sub(r'<[^>]+>', '', snippet).strip()

            if not title or title == "Product Hunt":
                continue

            signals.append(make_signal(
                title=title,
                url=url,
                source="producthunt",
                source_name="Product Hunt",
                category="tech_communities",
                language="en",
                snippet=snippet,
                raw_text=f"{title} {snippet}",
            ))
    except Exception as e:
        print(f"   PH异常: {e}")
    return signals


def _v2ex(tab="creative"):
    """V2EX 抓取"""
    signals = []
    try:
        html = _fetch_html(f"https://www.v2ex.com/?tab={tab}")
        # 新版V2EX HTML: 直接提取 /t/数字ID 的链接
        items = re.findall(
            r'<a[^>]*href="(/t/\d+)"[^>]*>([^<]+)</a>',
            html
        )
        seen = set()
        for url, title in items:
            title = title.strip()
            if title in seen or len(title) < 5:
                continue
            seen.add(title)
            full_url = "https://www.v2ex.com" + url
            signals.append(make_signal(
                title=title,
                url=full_url,
                source=f"v2ex_{tab}",
                source_name=f"V2EX {tab}",
                category="tech_communities",
                language="zh",
                snippet=title,
            ))
            if len(signals) >= 20:
                break
    except Exception as e:
        print(f"   V2EX ({tab}) 异常: {e}")
    return signals


def collect_tech_communities():
    """采集所有技术社区信号源"""
    sources = _load_sources()
    all_signals = []

    collectors = {
        "github_trending": _gh_trending,
        "hackernews": _hackernews,
        "producthunt": _producthunt,
        "v2ex_create": lambda: _v2ex("creative"),
        "v2ex_share": lambda: _v2ex("share"),
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
    signals = collect_tech_communities()
    for s in signals:
        print(f"  [{s.source_name}] {s.title[:60]}")
