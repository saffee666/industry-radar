from datetime import datetime
from src.collectors.base import BaseCollector
from src.models import RawSignal


class GitHubCollector(BaseCollector):
    """Scrape GitHub Trending page."""

    def __init__(self, config: dict | None = None):
        super().__init__("github", "GitHub Trending", config)

    def collect(self) -> list[RawSignal]:
        url = "https://github.com/trending?since=daily"
        resp = self.client.get(url)
        resp.raise_for_status()

        signals = []
        text = resp.text
        now = datetime.now().isoformat()

        # Parse trending repos from HTML
        import re
        repo_blocks = re.findall(
            r'<h2[^>]*class="[^"]*h3[^"]*lh-condensed[^"]*"[^>]*>.*?<\/h2>',
            text, re.DOTALL
        )

        for i, block in enumerate(repo_blocks[:25]):
            a_tags = re.findall(r'<a\s[^>]*href="([^"]*)"[^>]*>(.*?)<\/a>', block, re.DOTALL)
            if len(a_tags) >= 1:
                href = a_tags[0][0].strip()
                repo_path = href.strip("/")
                parts = repo_path.split("/")
                if len(parts) >= 2:
                    repo_name = f"{parts[0]}/{parts[1]}"
                else:
                    repo_name = repo_path

                # Clean HTML from text
                text_content = re.sub(r'<[^>]+>', '', a_tags[0][1]).strip()
                desc_match = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>(.*?)<\/p>', text, re.DOTALL)

                signals.append(RawSignal(
                    title=repo_name,
                    url=f"https://github.com/{repo_path}",
                    source=self.name,
                    source_name=self.display_name,
                    snippet=text_content or repo_name,
                    timestamp=now,
                    language="en",
                    metadata={"rank": i + 1}
                ))

        # Also parse description paragraphs for context
        desc_blocks = re.findall(
            r'<p[^>]*class="[^"]*col-9[^"]*color-fg-muted[^"]*"[^>]*>(.*?)<\/p>',
            text, re.DOTALL
        )
        for i, signal in enumerate(signals):
            if i < len(desc_blocks):
                desc = re.sub(r'<[^>]+>', '', desc_blocks[i]).strip()
                if desc:
                    signal.raw_text = desc

        return signals
