import re
from datetime import datetime
from src.collectors.base import BaseCollector
from src.models import RawSignal

_FEED_URL = "https://www.producthunt.com/feed?category=undefined"


class ProductHuntCollector(BaseCollector):
    """Collect Product Hunt trending products via Atom feed."""

    def __init__(self, config: dict | None = None):
        super().__init__("producthunt", "Product Hunt", config)

    def collect(self) -> list[RawSignal]:
        resp = self.client.get(_FEED_URL)
        resp.raise_for_status()

        text = resp.text
        now = datetime.now().isoformat()
        signals = []

        entries = re.findall(r"<entry>(.*?)</entry>", text, re.DOTALL)

        for i, entry in enumerate(entries[:25]):
            title_m = re.search(r"<title[^>]*>(.*?)</title>", entry, re.DOTALL)
            link_m = re.search(r'<link[^>]*href="([^"]+)"', entry)
            summary_m = re.search(
                r"<content[^>]*type=\"html\"[^>]*>(.*?)</content>", entry, re.DOTALL
            )

            title = title_m.group(1).strip() if title_m else ""
            link = link_m.group(1).strip() if link_m else ""
            summary = ""
            if summary_m:
                raw_content = summary_m.group(1)
            raw_content = raw_content.replace("&lt;", "<").replace("&gt;", ">")
            raw_content = raw_content.replace("&amp;", "&").replace("&quot;", '"')
            raw_content = raw_content.replace("&apos;", "'")
            summary = re.sub(r"<[^>]+>", "", raw_content).strip()[:200]

            if title:
                signals.append(RawSignal(
                    title=title,
                    url=link,
                    source=self.name,
                    source_name=self.display_name,
                    snippet=summary or title,
                    timestamp=now,
                    language="en",
                    metadata={"rank": i + 1},
                ))

        return signals
