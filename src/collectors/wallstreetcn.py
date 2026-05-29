import json
import re
from datetime import datetime
from src.collectors.base import BaseCollector
from src.models import RawSignal


class WallStreetCNCollector(BaseCollector):
    """Scrape 华尔街见闻 hot articles."""

    def __init__(self, config: dict | None = None):
        super().__init__("wallstreetcn", "华尔街见闻", config)

    def collect(self) -> list[RawSignal]:
        now = datetime.now().isoformat()
        signals = []

        # Try lives endpoint first (real-time news flashes)
        lives_url = "https://api-one.wallstcn.com/apiv1/content/lives?channel=global&limit=30"
        try:
            resp = self.client.get(lives_url)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", {}).get("items", []) or []

            for i, item in enumerate(items[:25]):
                title = (item.get("title") or "").strip()
                content = (item.get("content_text") or "").strip()
                if not title and content:
                    title = content[:60]

                signals.append(RawSignal(
                    title=title,
                    url=f"https://wallstreetcn.com/livenews/{item.get('id', '')}",
                    source=self.name,
                    source_name=self.display_name,
                    snippet=content[:200] if content else title,
                    raw_text=content,
                    timestamp=now,
                    language="zh",
                    metadata={"rank": i + 1}
                ))
        except Exception:
            pass

        if signals:
            return signals

        # Fallback: hot articles endpoint
        try:
            url = "https://api-one.wallstcn.com/apiv1/content/articles/hot?period=all"
            resp = self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            articles = data.get("data", {}).get("day_items", []) or []

            for i, article in enumerate(articles[:25]):
                title = (article.get("title") or "").strip()
                signals.append(RawSignal(
                    title=title,
                    url=article.get("uri", ""),
                    source=self.name,
                    source_name=self.display_name,
                    snippet="",
                    timestamp=now,
                    language="zh",
                    metadata={"rank": i + 1}
                ))
        except Exception:
            pass

        if not signals:
            return self._scrape_html()

        return signals

    def _scrape_html(self) -> list[RawSignal]:
        url = "https://wallstreetcn.com/"
        resp = self.client.get(url)
        resp.raise_for_status()
        text = resp.text
        now = datetime.now().isoformat()

        signals = []
        # Try to extract article links
        articles = re.findall(
            r'<a[^>]*href="(/articles/\d+)"[^>]*>(.*?)</a>',
            text, re.DOTALL
        )

        for i, (href, raw_title) in enumerate(articles[:25]):
            title = re.sub(r'<[^>]+>', '', raw_title).strip()
            if title and len(title) > 3:
                signals.append(RawSignal(
                    title=title,
                    url=f"https://wallstreetcn.com{href}",
                    source=self.name,
                    source_name=self.display_name,
                    snippet=title,
                    timestamp=now,
                    language="zh",
                    metadata={"rank": i + 1}
                ))

        return signals
