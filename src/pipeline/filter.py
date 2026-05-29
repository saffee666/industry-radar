import json
import yaml
from pathlib import Path
from src.models import RawSignal, FilterResult
from src.pipeline.llm_client import chat_json

_PROMPTS: dict | None = None


def _load_prompts() -> dict:
    global _PROMPTS
    if _PROMPTS is None:
        path = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"
        with open(path, encoding="utf-8") as f:
            _PROMPTS = yaml.safe_load(f)
    return _PROMPTS


def filter_signals(raw_signals: list[RawSignal], batch_size: int = 50) -> FilterResult:
    """Filter raw signals: keep only those with potential arbitrage value.

    Uses LLM batch processing. Returns FilterResult with passed/rejected.
    """
    if not raw_signals:
        return FilterResult(passed=[], rejected=[], reason_map={})

    prompts = _load_prompts()
    filter_config = prompts["filter"]

    passed: list[RawSignal] = []
    rejected: list[RawSignal] = []
    reason_map: dict[str, str] = {}

    # Process in batches to keep prompt size manageable
    for batch_start in range(0, len(raw_signals), batch_size):
        batch = raw_signals[batch_start:batch_start + batch_size]

        # Build items text
        items_lines = []
        for i, sig in enumerate(batch):
            idx = batch_start + i
            text = f"[{idx}] [{sig.source_name}] {sig.title}"
            if sig.snippet:
                text += f"\n    摘要: {sig.snippet[:120]}"
            items_lines.append(text)

        user_msg = filter_config["user_template"].format(
            count=len(batch),
            items="\n\n".join(items_lines),
        )

        response = chat_json(
            system_prompt=filter_config["system"],
            user_message=user_msg,
            temperature=0.1,
        )

        # Parse JSON from response — handle JSON array and line-by-line
        parsed = []
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            arr = json.loads(cleaned)
            if isinstance(arr, list):
                parsed = arr
        except json.JSONDecodeError:
            for line in response.strip().split("\n"):
                line = line.strip().strip(",")
                if not line or line.startswith("`") or line in ("[", "]"):
                    continue
                try:
                    parsed.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        batch_passed = 0
        batch_marked = set()
        for result in parsed:
            absolute_idx = result.get("index", -1)
            local_idx = absolute_idx - batch_start
            if not (0 <= local_idx < len(batch)):
                continue
            batch_marked.add(local_idx)
            sig = batch[local_idx]
            if result.get("pass", False):
                passed.append(sig)
                batch_passed += 1
            else:
                rejected.append(sig)
                reason_map[sig.title + (sig.url or "")] = result.get("reason", "")

        # Fallback: if less than 50% of batch was parsed, pass the rest through
        if len(parsed) < len(batch) * 0.5:
            for i, sig in enumerate(batch):
                if i not in batch_marked:
                    passed.append(sig)

    return FilterResult(passed=passed, rejected=rejected, reason_map=reason_map)
