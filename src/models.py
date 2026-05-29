from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SignalType(Enum):
    DEMAND = "demand"       # 需求端 — real user needs/pain points
    SUPPLY = "supply"       # 供给端 — new products/tools/solutions
    POLICY = "policy"       # 政策端 — regulation changes
    MARKET = "market"       # 市场端 — capital/valuation/trend shifts
    COMPETITOR = "competitor"  # 竞品端 — competitor moves
    OPPORTUNITY = "opportunity"  # 机会端 — emerging gaps


class Industry(Enum):
    AI = "ai"
    CONTENT = "content"
    SAAS = "saas"
    NEW_ENERGY = "newenergy"
    CONSUMER = "consumer"
    ECOMMERCE = "ecommerce"
    FINTECH = "fintech"
    OVERSEAS = "overseas"
    OTHER = "other"


INDUSTRY_LABELS = {
    "ai": "AI/大模型",
    "content": "短剧/内容产业",
    "saas": "SaaS/企服",
    "newenergy": "新能源/碳中和",
    "consumer": "消费品牌",
    "ecommerce": "电商/零售",
    "fintech": "金融科技",
    "overseas": "出海/跨境",
    "other": "其他",
}


@dataclass
class RawSignal:
    title: str
    url: str
    source: str              # collector key e.g. "github", "36kr"
    source_name: str         # display name e.g. "GitHub Trending"
    snippet: str             # short description or hot value
    raw_text: str = ""       # full scraped text if available
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    language: str = "zh"
    metadata: dict = field(default_factory=dict)


@dataclass
class AnalyzedSignal:
    title: str
    url: str
    source_name: str
    industry: str            # Industry enum value
    industry_name: str       # display label
    signal_type: str         # SignalType enum value
    signal_type_name: str    # display label

    # 5-dimension scores (1-10)
    demand_score: float = 0.0       # 需求真实性
    supply_gap_score: float = 0.0   # 供给缺口度
    window_score: float = 0.0       # 窗口紧迫性
    monetization_score: float = 0.0 # 变现直接性
    feasibility_score: float = 0.0  # 进入可行性
    composite_score: float = 0.0    # weighted composite

    # analysis layer
    why_important: str = ""         # 一句话：为什么重要
    window_estimate: str = ""       # 预估窗口期 e.g. "1-2周"
    suggested_action: str = ""      # 建议行动
    risk_note: str = ""             # 风险提示

    # metadata
    signal_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    raw: RawSignal | None = None


@dataclass
class DailyBrief:
    date: str
    total_collected: int
    total_filtered: int
    high_priority_count: int        # composite >= 8.0
    opportunities: list[AnalyzedSignal]  # top 3-5
    industry_signals: list[AnalyzedSignal]  # 10-15 by industry
    anomalies: list[str]            # anomaly notes
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FilterResult:
    passed: list[RawSignal]
    rejected: list[RawSignal]
    reason_map: dict[str, str]     # signal_id -> rejection reason
