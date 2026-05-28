"""采集器基类：统一接口 + 标准化输出"""

import hashlib
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Signal:
    """标准化信号数据"""
    title: str
    url: str
    source: str          # 信源ID, 如 "github_trending"
    source_name: str     # 信源中文名, 如 "GitHub Trending"
    category: str        # 信源大类: tech_communities / chinese_platforms / ...
    raw_text: str        # 原始文本(标题+摘要)
    snippet: str         # 简短摘要(用于晨报显示)
    timestamp: str       # ISO格式时间
    language: str        # zh / en
    metadata: dict = field(default_factory=dict)  # 额外信息(热度/价格等)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["signal_id"] = self.signal_id()
        return d

    def signal_id(self) -> str:
        """生成唯一ID：URL + 标题的hash"""
        content = f"{self.url}{self.title}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


def make_signal(
    title: str,
    url: str = "",
    source: str = "",
    source_name: str = "",
    category: str = "",
    snippet: str = "",
    language: str = "zh",
    raw_text: str = "",
    metadata: Optional[dict] = None,
) -> Signal:
    """标准化生成Signal对象"""
    return Signal(
        title=title.strip(),
        url=url.strip(),
        source=source,
        source_name=source_name,
        category=category,
        raw_text=raw_text or title,
        snippet=snippet or title[:80],
        timestamp=datetime.now().isoformat(),
        language=language,
        metadata=metadata or {},
    )
