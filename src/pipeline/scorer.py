from src.models import AnalyzedSignal


def rank_signals(signals: list[AnalyzedSignal]) -> list[AnalyzedSignal]:
    """Sort by composite score descending."""
    return sorted(signals, key=lambda s: s.composite_score, reverse=True)


def top_opportunities(signals: list[AnalyzedSignal], n: int = 5) -> list[AnalyzedSignal]:
    """Return top N signals as opportunities."""
    ranked = rank_signals(signals)
    return ranked[:n]


def by_industry(signals: list[AnalyzedSignal]) -> dict[str, list[AnalyzedSignal]]:
    """Group signals by industry."""
    groups: dict[str, list[AnalyzedSignal]] = {}
    for s in signals:
        groups.setdefault(s.industry, []).append(s)
    for v in groups.values():
        v.sort(key=lambda x: x.composite_score, reverse=True)
    return dict(sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True))


def high_priority(signals: list[AnalyzedSignal], threshold: float = 8.0) -> list[AnalyzedSignal]:
    return [s for s in signals if s.composite_score >= threshold]


def medium_priority(signals: list[AnalyzedSignal], threshold: float = 6.0) -> list[AnalyzedSignal]:
    return [s for s in signals if threshold <= s.composite_score < 8.0]
