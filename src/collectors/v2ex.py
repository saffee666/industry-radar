import re
from datetime import datetime
from src.collectors.base import BaseCollector
from src.models import RawSignal


class V2EXCollector(BaseCollector):
    """Collect from V2EX creative and share tabs via HTML scraping.

    Supports config keys:
        tabs: list of tab names, default ["creative", "share"]
    """

    def __init__(self, config: dict | None = None):
        super().__init__("v2ex", "V2EX", config)

    def collect(self) -> list[RawSignal]:
        tabs = self.config.get("tabs", ["creative", "share"])
        signals = []
        now = datetime.now().isoformat()

        for tab in tabs:
            try:
                url = f"https://www.v2ex.com/?tab={tab}"
                resp = self.client.get(url)
                resp.raise_for_status()
                text = resp.text

                # Parse topic cells: <span class="item_title"><a href="/t/...">title</a></span>
                items = re.findall(
                    r'<span\s+class="item_title">\s*<a\s+href="(/t/\d+[^"]*)"[^>]*>(.*?)</a>',
                    text, re.DOTALL
                )

                for href, title in items[:15]:
                    clean_title = re.sub(r'<[^>]+>', '', title).strip()
                    if clean_title:
                        signals.append(RawSignal(
                            title=clean_title,
                            url=f"https://www.v2ex.com{href}",
                            source=f"v2ex_{tab}",
                            source_name=f"V2EX {tab.title()}",
                            snippet=clean_title,
                            timestamp=now,
                            language="zh",
                            metadata={"tab": tab}
                        ))
            except Exception:
                continue

        return signals
