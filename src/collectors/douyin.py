import json
import re
from datetime import datetime
from src.collectors.base import BaseCollector
from src.models import RawSignal


class DouyinCollector(BaseCollector):
    """Collect Douyin hot search/trending.

    Config keys:
        max_items: max items per category (default 15)
    """

    def __init__(self, config: dict | None = None):
        super().__init__("douyin", "抖音热搜", config)
        self.max_items = self.config.get("max_items", 15)

    def collect(self) -> list[RawSignal]:
        now = datetime.now().isoformat()
        signals = []

        # Try Douyin hot search API
        # Note: Douyin API changes frequently; this endpoint may need updating
        urls_to_try = [
            "https://www.douyin.com/aweme/v1/web/hot/search/list/",
            "https://www.douyin.com/aweme/v1/web/hot/search/list/?detail_list=0",
        ]

        for api_url in urls_to_try:
            try:
                headers = {
                    "Referer": "https://www.douyin.com/",
                    "Accept": "application/json",
                }
                resp = self.client.get(api_url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                word_list = (
                    data.get("data", {})
                    .get("word_list", []) or []
                )

                for i, item in enumerate(word_list[:self.max_items]):
                    word = (item.get("word") or "").strip()
                    if not word:
                        continue
                    signals.append(RawSignal(
                        title=word,
                        url=f"https://www.douyin.com/search/{word}",
                        source=self.name,
                        source_name=self.display_name,
                        snippet=f"热度: {item.get('hot_value', 0)}",
                        timestamp=now,
                        language="zh",
                        metadata={
                            "rank": i + 1,
                            "hot_value": item.get("hot_value", 0),
                            "position": item.get("position", i + 1),
                        }
                    ))

                if signals:
                    break
            except Exception:
                continue

        # Fallback: try to scrape trending from main page
        if not signals:
            try:
                resp = self.client.get(
                    "https://www.douyin.com/",
                    headers={"Referer": "https://www.douyin.com/"}
                )
                text = resp.text

                # Try to find JSON data in script tags
                json_data = re.findall(
                    r'window\._NUXT_\s*=\s*({.*?});',
                    text, re.DOTALL
                )
                if not json_data:
                    json_data = re.findall(
                        r'__NEXT_DATA__\s*=\s*({.*?});',
                        text, re.DOTALL
                    )

                # If we found data, try to extract trending
                # This is best-effort due to frequent API changes
            except Exception:
                pass

        return signals
