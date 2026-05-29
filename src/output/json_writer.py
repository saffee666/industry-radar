import json
from pathlib import Path
from datetime import datetime
from src.models import RawSignal, AnalyzedSignal


def save_raw_signals(signals: list[RawSignal], output_dir: str | Path):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = output_dir / f"signals_{date_str}.json"

    data = []
    for s in signals:
        data.append({
            "title": s.title,
            "url": s.url,
            "source": s.source,
            "source_name": s.source_name,
            "snippet": s.snippet,
            "raw_text": s.raw_text,
            "timestamp": s.timestamp,
            "language": s.language,
            "metadata": s.metadata,
        })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_analyzed_signals(signals: list[AnalyzedSignal], output_dir: str | Path):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = output_dir / f"analyzed_{date_str}.json"

    data = []
    for s in signals:
        data.append({
            "signal_id": s.signal_id,
            "title": s.title,
            "url": s.url,
            "source_name": s.source_name,
            "industry": s.industry,
            "industry_name": s.industry_name,
            "signal_type": s.signal_type,
            "signal_type_name": s.signal_type_name,
            "scores": {
                "demand": s.demand_score,
                "supply_gap": s.supply_gap_score,
                "window": s.window_score,
                "monetization": s.monetization_score,
                "feasibility": s.feasibility_score,
                "composite": s.composite_score,
            },
            "why_important": s.why_important,
            "window_estimate": s.window_estimate,
            "suggested_action": s.suggested_action,
            "risk_note": s.risk_note,
        })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
