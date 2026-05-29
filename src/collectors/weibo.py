import json
import re
from datetime import datetime
from src.collectors.base import BaseCollector
from src.models import RawSignal


class WeiboCollector(BaseCollector):
    """Collect Weibo hot search. Uses the mobile API endpoint.

    Config keys:
        max_items: max items (default 15)
    """

    def __init__(self, config: dict | None = None):
        super().__init__("weibo", "微博热搜", config)
        self.max_items = self.config.get("max_items", 15)

    def collect(self) -> list[RawSignal]:
        now = datetime.now().isoformat()
        signals = []

        # Try mobile API first
        url = "https://weibo.com/ajax/side/hotSearch"
        headers = {
            "Referer": "https://weibo.com/",
            "Accept": "application/json",
        }
        try:
            resp = self.client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            items = (
                data.get("data", {})
                .get("realtime", [])
            )
            if not items:
                items = data.get("data", []) if isinstance(data.get("data"), list) else []

            for i, item in enumerate(items[:self.max_items]):
                word = (item.get("word") or item.get("note") or "").strip()
                if not word:
                    continue

                raw_hot = item.get("raw_hot") or item.get("num") or 0
                signals.append(RawSignal(
                    title=word,
                    url=f"https://s.weibo.com/weibo?q={word}",
                    source=self.name,
                    source_name=self.display_name,
                    snippet=f"热度: {raw_hot}",
                    timestamp=now,
                    language="zh",
                    metadata={
                        "rank": i + 1,
                        "hot_value": raw_hot,
                        "category": item.get("category", ""),
                    }
                ))
            return signals
        except Exception:
            pass

        # Fallback: scrape HTML
        try:
            resp = self.client.get("https://weibo.com/ajax/statuses/hot_band")
            data = resp.json()
            band_list = data.get("data", {}).get("band_list", [])
            for i, item in enumerate(band_list[:self.max_items]):
                word = item.get("word", "").strip()
                if word:
                    signals.append(RawSignal(
                        title=word,
                        url=f"https://s.weibo.com/weibo?q={word}",
                        source=self.name,
                        source_name=self.display_name,
                        snippet=f"热度: {item.get('raw_hot', 0)}",
                        timestamp=now,
                        language="zh",
                        metadata={
                            "rank": i + 1,
                            "hot_value": item.get("raw_hot", 0),
                            "category": item.get("category", ""),
                        }
                    ))
        except Exception:
            pass

        return signals
