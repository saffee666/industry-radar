import re
from datetime import datetime
from src.collectors.base import BaseCollector
from src.models import RawSignal


class RSSCollector(BaseCollector):
    """Generic RSS/Atom feed collector.

    Config keys:
        feed_url: RSS feed URL
        max_items: max items to collect (default 25)
    """

    def __init__(self, name: str, display_name: str, config: dict | None = None):
        super().__init__(name, display_name, config)
        self.feed_url = self.config.get("feed_url", "")
        self.max_items = self.config.get("max_items", 25)

    def collect(self) -> list[RawSignal]:
        if not self.feed_url:
            return []

        resp = self.client.get(self.feed_url)
        resp.raise_for_status()
        text = resp.text
        now = datetime.now().isoformat()

        # Parse RSS items: <item>...</item>
        items = re.findall(r'<item>(.*?)</item>', text, re.DOTALL)
        if not items:
            # Try Atom: <entry>...</entry>
            items = re.findall(r'<entry>(.*?)</entry>', text, re.DOTALL)

        signals = []
        for i, item_text in enumerate(items[:self.max_items]):
            title_m = re.search(r'<title[^>]*>(.*?)</title>', item_text, re.DOTALL)
            link_m = re.search(r'<link[^>]*href="([^"]*)"', item_text, re.DOTALL)
            if not link_m:
                link_m = re.search(r'<link[^>]*>(.*?)</link>', item_text, re.DOTALL)
            desc_m = re.search(r'<description[^>]*>(.*?)</description>', item_text, re.DOTALL)
            if not desc_m:
                desc_m = re.search(r'<content[^>]*>(.*?)</content>', item_text, re.DOTALL)

            title = title_m.group(1).strip() if title_m else ""
            title = re.sub(r'<[^>]+>', '', title)
            title = title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')

            link = (link_m.group(1) or link_m.group(2) if link_m and link_m.lastindex else "").strip() if link_m else ""
            link = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', link)

            snippet = ""
            if desc_m:
                desc = desc_m.group(1)
                desc = re.sub(r'<[^>]+>', '', desc)
                desc = desc.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
                snippet = desc[:200]

            if title:
                signals.append(RawSignal(
                    title=title,
                    url=link,
                    source=self.name,
                    source_name=self.display_name,
                    snippet=snippet,
                    raw_text=snippet,
                    timestamp=now,
                    language="zh" if any('一' <= c <= '鿿' for c in title) else "en",
                    metadata={"rank": i + 1}
                ))

        return signals
