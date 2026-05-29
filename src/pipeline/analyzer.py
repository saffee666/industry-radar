import json
import hashlib
import yaml
from pathlib import Path
from src.models import RawSignal, AnalyzedSignal
from src.pipeline.llm_client import chat_json

_PROMPTS: dict | None = None
_INDUSTRIES: dict | None = None


def _load_prompts() -> dict:
    global _PROMPTS
    if _PROMPTS is None:
        path = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"
        with open(path, encoding="utf-8") as f:
            _PROMPTS = yaml.safe_load(f)
    return _PROMPTS


def _load_industries() -> dict:
    global _INDUSTRIES
    if _INDUSTRIES is None:
        path = Path(__file__).parent.parent.parent / "config" / "industries.yaml"
        with open(path, encoding="utf-8") as f:
            _INDUSTRIES = yaml.safe_load(f)
    return _INDUSTRIES


def _parse_json_response(response: str) -> list[dict]:
    """Parse LLM response which may be JSON array or line-by-line JSON."""
    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    # Try full response as JSON array
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Fallback: line-by-line JSON objects
    results = []
    for line in cleaned.split("\n"):
        line = line.strip().strip(",")
        if not line or line.startswith("```") or line in ("[", "]"):
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return results


def analyze_signals(
    raw_signals: list[RawSignal],
    mode: str = "default",
    batch_size: int = 10,
) -> list[AnalyzedSignal]:
    """Analyze signals: classify industry + 5-dim score + judgment.

    mode: "default" (自己做项目), "info_broker" (信息中介), "traffic_arb" (流量套利)
    """
    if not raw_signals:
        return []

    prompts = _load_prompts()
    analyzer_config = prompts["analyzer"]
    scorer_config = prompts["scorer"]
    weights = scorer_config.get("weights", {}).get(mode, scorer_config["weights"]["default"])

    analyzed: list[AnalyzedSignal] = []

    for batch_start in range(0, len(raw_signals), batch_size):
        batch = raw_signals[batch_start:batch_start + batch_size]

        items_lines = []
        for i, sig in enumerate(batch):
            idx = batch_start + i
            text = f"[{idx}] 标题: {sig.title}"
            if sig.raw_text:
                text += f"\n    全文: {sig.raw_text[:300]}"
            elif sig.snippet:
                text += f"\n    摘要: {sig.snippet[:200]}"
            text += f"\n    来源: {sig.source_name}"
            items_lines.append(text)

        user_msg = analyzer_config["user_template"].format(
            count=len(batch),
            items="\n\n".join(items_lines) + "\n\n按JSON格式逐条输出分析结果。",
        )

        try:
            response = chat_json(
                system_prompt=analyzer_config["system"],
                user_message=user_msg,
                temperature=0.3,
                max_tokens=8192,
            )
        except Exception as e:
            print(f"  [analyzer batch {batch_start}] LLM error: {e}")
            continue

        if not response.strip():
            print(f"  [analyzer batch {batch_start}] empty response, skipping")
            continue

        print(f"  [analyzer batch {batch_start}] LLM returned {len(response)} chars")

        parsed = _parse_json_response(response)
        industries_data = _load_industries().get("industries", {})
        signal_type_labels = {
            "demand": "需求端", "supply": "供给端",
            "policy": "政策端", "market": "市场端",
            "competitor": "竞品端", "opportunity": "机会端",
        }

        for data in parsed:
            absolute_idx = data.get("index", -1)
            local_idx = absolute_idx - batch_start
            if not (0 <= local_idx < len(batch)):
                continue
            sig = batch[local_idx]
            scores = data.get("scores", {})

            demand = float(scores.get("demand", 5))
            supply_gap = float(scores.get("supply_gap", 5))
            window = float(scores.get("window", 5))
            monetization = float(scores.get("monetization", 5))
            feasibility = float(scores.get("feasibility", 5))

            composite = round(
                demand * weights.get("demand", 0.25)
                + supply_gap * weights.get("supply_gap", 0.25)
                + window * weights.get("window", 0.15)
                + monetization * weights.get("monetization", 0.15)
                + feasibility * weights.get("feasibility", 0.20),
                1
            )

            industry_code = data.get("industry", "other")
            signal_type_code = data.get("signal_type", "market")
            ind_info = industries_data.get(industry_code, {})
            ind_label = ind_info.get("name", "其他") if isinstance(ind_info, dict) else industry_code
            st_label = signal_type_labels.get(signal_type_code, "市场端")

            signal_id = hashlib.md5((sig.title + (sig.url or "")).encode()).hexdigest()[:12]

            analyzed.append(AnalyzedSignal(
                title=sig.title, url=sig.url,
                source_name=sig.source_name,
                industry=industry_code, industry_name=ind_label,
                signal_type=signal_type_code, signal_type_name=st_label,
                demand_score=demand, supply_gap_score=supply_gap,
                window_score=window, monetization_score=monetization,
                feasibility_score=feasibility, composite_score=composite,
                why_important=data.get("why_important", ""),
                window_estimate=data.get("window_estimate", ""),
                suggested_action=data.get("suggested_action", ""),
                risk_note=data.get("risk_note", ""),
                signal_id=signal_id, raw=sig,
            ))

    return analyzed
