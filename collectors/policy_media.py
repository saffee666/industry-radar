"""政策 & 行业媒体采集器: 36氪, 虎嗅, 晚点, TechCrunch, 国务院政策"""

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
    return [s for s in config["sources"]["policy_media"] if s.get("enabled")]


def _36kr():
    """36氪 — RSS feed (绕过WAF)"""
    import xml.etree.ElementTree as ET
    signals = []
    try:
        resp = requests.get(
            "https://36kr.com/feed",
            headers=HEADERS,
            timeout=15
        )
        if resp.status_code == 200:
            try:
                root = ET.fromstring(resp.text)
            except ET.ParseError:
                # XML偶尔有非法字符，清洗后重试
                cleaned = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\x80-\xFF]', '', resp.text)
                try:
                    root = ET.fromstring(cleaned)
                except ET.ParseError:
                    # 回退到正则提取
                    items = re.findall(r'<item>(.*?)</item>', resp.text, re.DOTALL)
                    for item_text in items[:25]:
                        t = re.search(r'<title>(.*?)</title>', item_text)
                        l = re.search(r'<link>(.*?)</link>', item_text)
                        d = re.search(r'<description>(.*?)</description>', item_text)
                        p = re.search(r'<pubDate>(.*?)</pubDate>', item_text)
                        title = t.group(1).strip() if t else ""
                        url = l.group(1).strip() if l else ""
                        if title:
                            url = re.sub(r'\?f=rss$', '', url) if url else ""
                            snippet = re.sub(r'<[^>]+>', '', d.group(1)).strip()[:150] if d else ""
                            signals.append(make_signal(
                                title=title, url=url, source="36kr", source_name="36氪",
                                category="policy_media", language="zh",
                                snippet=snippet, raw_text=f"{title}",
                                metadata={"publish_time": p.group(1) if p else ""}
                            ))
                    return signals
            for item in list(root.iter("item"))[:25]:
                title_el = item.find("title")
                link_el = item.find("link")
                pubdate_el = item.find("pubDate")
                desc_el = item.find("description")

                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                url = link_el.text.strip() if link_el is not None and link_el.text else ""
                pubdate = pubdate_el.text.strip() if pubdate_el is not None and pubdate_el.text else ""
                desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

                # 清除URL中的?f=rss参数
                url = re.sub(r'\?f=rss$', '', url)

                # 清理HTML标签取纯文本摘要
                snippet = re.sub(r'<[^>]+>', '', desc).strip()[:150] if desc else ""

                if title:
                    signals.append(make_signal(
                        title=title,
                        url=url,
                        source="36kr",
                        source_name="36氪",
                        category="policy_media",
                        language="zh",
                        snippet=snippet,
                        raw_text=f"{title} {desc}",
                        metadata={"publish_time": pubdate}
                    ))
    except Exception as e:
        print(f"   36氪异常: {e}")
    return signals


def _huxiu():
    """虎嗅 — 暂不可用(WAF拦截)"""
    signals = []
    try:
        import xml.etree.ElementTree as ET
        resp = requests.get("https://www.huxiu.com/rss/0.xml", headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            root = ET.fromstring(resp.text)
            for item in list(root.iter("item"))[:20]:
                t = item.find("title")
                l = item.find("link")
                d = item.find("description")
                title = t.text.strip() if t is not None and t.text else ""
                url = l.text.strip() if l is not None and l.text else ""
                if title:
                    snippet = re.sub(r'<[^>]+>', '', d.text).strip()[:150] if d is not None and d.text else ""
                    signals.append(make_signal(
                        title=title, url=url, source="huxiu", source_name="虎嗅",
                        category="policy_media", language="zh",
                        snippet=snippet, raw_text=f"{title}"
                    ))
    except Exception as e:
        print(f"   虎嗅异常: {e}")
    return signals


def _wallstreetcn():
    """华尔街见闻 — 实时财经快讯，公开API无需登录"""
    signals = []
    try:
        resp = requests.get(
            "https://api-one.wallstcn.com/apiv1/content/lives",
            params={"channel": "global-channel", "limit": 30},
            headers=HEADERS, timeout=15
        )
        if resp.status_code != 200:
            return signals
        data = resp.json()
        if data.get("code") != 20000:
            return signals
        items = data.get("data", {}).get("items", [])
        for it in items:
            title = it.get("title", "")
            content = it.get("content", "")
            # 优先用title，否则用content_text提取
            if not title:
                content_text = it.get("content_text", "")
                title = content_text[:80] if content_text else (re.sub(r'<[^>]+>', '', content).strip()[:80] if content else "")
            if title:
                snippet = re.sub(r'<[^>]+>', '', content).strip()[:150] if content else ""
                signals.append(make_signal(
                    title=title,
                    url=f"https://wallstreetcn.com/lives/{it.get('id','')}",
                    source="wallstreetcn",
                    source_name="华尔街见闻",
                    category="policy_media",
                    language="zh",
                    snippet=snippet,
                    raw_text=f"{title} {snippet}",
                    metadata={"publish_time": it.get("display_time", "")}
                ))
    except Exception as e:
        print(f"   华尔街见闻异常: {e}")
    return signals


def _ifanr():
    """爱范儿 — HTML抓取"""
    signals = []
    try:
        resp = requests.get(
            "https://www.ifanr.com/",
            headers={**HEADERS, "Accept-Language": "zh-CN,zh;q=0.9"},
            timeout=15
        )
        if resp.status_code == 200:
            html = resp.text
            items = re.findall(
                r'href="(https?://www\.ifanr\.com/(\d+))"[^>]*>\s*([^<]{5,200}?)\s*</a>',
                html
            )
            seen = set()
            for url, aid, title in items:
                title = title.strip()
                if aid in seen or len(title) < 5:
                    continue
                seen.add(aid)
                signals.append(make_signal(
                    title=title,
                    url=url,
                    source="ifanr",
                    source_name="爱范儿",
                    category="policy_media",
                    language="zh",
                    snippet=title,
                ))
                if len(signals) >= 20:
                    break
    except Exception as e:
        print(f"   爱范儿异常: {e}")
    return signals


def _latepost():
    """晚点LatePost — 静态HTML可抓取约10篇精选文章"""
    signals = []
    try:
        html = requests.get("https://www.latepost.com/", headers=HEADERS, timeout=15).text
        # 新版晚点URL格式: /news/dj_detail?id=XXXX
        items = re.findall(r'<a[^>]*href="(/news/dj_detail\?id=\d+)"[^>]*>([^<]{8,})</a>', html)
        seen_urls = set()
        for url, title in items:
            title = title.strip()
            # 过滤掉Q&A摘要片段和导航标签
            if 'Q:' in title or 'A:' in title:
                continue
            if url in seen_urls or len(title) < 8:
                continue
            seen_urls.add(url)
            signals.append(make_signal(
                title=title,
                url="https://www.latepost.com" + url,
                source="latepost",
                source_name="晚点LatePost",
                category="policy_media",
                language="zh",
                snippet=title,
            ))
    except Exception as e:
        print(f"   晚点异常: {e}")
    return signals


def _techcrunch():
    """TechCrunch"""
    signals = []
    try:
        resp = requests.get(
            "https://techcrunch.com/wp-json/wp/v2/posts",
            params={"per_page": 20, "_embed": "true"},
            headers=HEADERS,
            timeout=15
        )
        if resp.status_code == 200:
            posts = resp.json()
            for post in posts[:20]:
                title = post.get("title", {}).get("rendered", "")
                excerpt = post.get("excerpt", {}).get("rendered", "")
                excerpt = re.sub(r'<[^>]+>', '', excerpt)[:150]
                signals.append(make_signal(
                    title=title,
                    url=post.get("link", ""),
                    source="techcrunch",
                    source_name="TechCrunch",
                    category="policy_media",
                    language="en",
                    snippet=excerpt,
                    raw_text=f"{title} {excerpt}",
                    metadata={"publish_time": post.get("date", "")}
                ))
    except Exception as e:
        print(f"   TechCrunch异常: {e}")
    return signals


def _gov_policy():
    """国务院政策文件库"""
    signals = []
    try:
        resp = requests.get(
            "https://www.gov.cn/zhengce/zhengcewenjianku/",
            headers=HEADERS,
            timeout=20
        )
        if resp.status_code == 200:
            html = resp.text
            # 提取政策列表
            items = re.findall(r'<a[^>]*href="([^"]*content[^"]*)"[^>]*title="([^"]*)"[^>]*>', html)
            for url, title in items[:15]:
                url = url if url.startswith("http") else "https://www.gov.cn" + url
                signals.append(make_signal(
                    title=title.strip(),
                    url=url,
                    source="gov_policy",
                    source_name="国务院政策",
                    category="policy_media",
                    language="zh",
                    snippet=f"政策文件: {title.strip()}",
                ))
    except Exception as e:
        print(f"   国务院政策异常: {e}")
    return signals


def collect_policy_media():
    """采集所有政策/媒体信号源"""
    import yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    sources = [s for s in config["sources"]["policy_media"] if s.get("enabled")]

    all_signals = []

    collectors = {
        "36kr": _36kr,
        "huxiu": _huxiu,
        "ifanr": _ifanr,
        "latepost": _latepost,
        "techcrunch": _techcrunch,
        "gov_policy": _gov_policy,
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
    signals = collect_policy_media()
    for s in signals:
        print(f"  [{s.source_name}] {s.title[:60]}")
