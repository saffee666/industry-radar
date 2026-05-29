#!/usr/bin/env python3
"""Industry Radar — 套利信号发现引擎.

Usage:
    python main.py                  # Full run: collect + filter + analyze + output
    python main.py --dry-run        # Collect only, no LLM calls
    python main.py --source github,36kr  # Only specified sources
    python main.py --mode info_broker    # Weight mode: info_broker/traffic_arb/default
    python main.py --mode quick     # 3 core sources, skip optional
"""

import argparse
import sys
import yaml
from pathlib import Path
from datetime import datetime

from src.collectors import (
    GitHubCollector, ProductHuntCollector, V2EXCollector,
    RSSCollector, WallStreetCNCollector, WeiboCollector, DouyinCollector,
)
from src.pipeline import filter_signals, analyze_signals, high_priority
from src.output import format_brief, save_raw_signals, save_analyzed_signals

PROJECT_DIR = Path(__file__).parent


def load_sources_config():
    path = PROJECT_DIR / "config" / "sources.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]


def create_collector(name: str, cfg: dict):
    collector_type = cfg.get("collector", name)
    display = cfg.get("name", name)

    collectors_map = {
        "github": lambda: GitHubCollector(cfg),
        "producthunt": lambda: ProductHuntCollector(cfg),
        "v2ex": lambda: V2EXCollector(cfg),
        "http_rss": lambda: RSSCollector(name, display, {"feed_url": cfg.get("url", ""), "max_items": 25}),
        "wallstreetcn": lambda: WallStreetCNCollector(cfg),
        "weibo": lambda: WeiboCollector(cfg),
        "douyin": lambda: DouyinCollector(cfg),
    }

    factory = collectors_map.get(collector_type)
    if factory:
        return factory()

    # Default: RSS collector
    return RSSCollector(name, display, {"feed_url": cfg.get("url", ""), "max_items": 25})


def run(args: argparse.Namespace):
    sources_config = load_sources_config()

    # Determine which sources to run
    if args.source:
        requested = set(s.strip() for s in args.source.split(","))
        active_sources = {k: v for k, v in sources_config.items() if k in requested}
    elif args.mode == "quick":
        quick_sources = ["github", "producthunt", "v2ex_creative"]
        active_sources = {k: v for k, v in sources_config.items()
                          if k in quick_sources and v.get("enabled", True)}
    else:
        active_sources = {k: v for k, v in sources_config.items() if v.get("enabled", True)}

    if not active_sources:
        print("No active sources found.")
        return

    print(f"Collecting from {len(active_sources)} sources: {', '.join(active_sources.keys())}")

    # Phase 1: Collect
    all_signals = []
    for name, cfg in active_sources.items():
        try:
            print(f"  [{name}] {cfg.get('name', name)}...", end=" ")
            collector = create_collector(name, cfg)
            signals = collector.collect()
            collector.close()
            print(f"{len(signals)} signals")
            all_signals.extend(signals)
        except Exception as e:
            print(f"FAILED: {e}")

    # Deduplicate by title+url
    seen = set()
    deduped = []
    for sig in all_signals:
        key = (sig.title.strip(), (sig.url or "").strip())
        if key not in seen:
            seen.add(key)
            deduped.append(sig)
    all_signals = deduped
    print(f"After dedup: {len(all_signals)}")

    if args.dry_run:
        print("--dry-run: stopping after collection. No LLM calls made.")
        save_raw_signals(all_signals, PROJECT_DIR / "raw")
        print(f"Raw signals saved to raw/")
        return

    if not all_signals:
        print("No signals collected.")
        return

    # Phase 2: Filter
    print("\nFiltering...")
    filter_result = filter_signals(all_signals)
    passed = filter_result.passed
    print(f"Passed: {len(passed)} / Rejected: {len(filter_result.rejected)}")

    # Save raw
    save_raw_signals(all_signals, PROJECT_DIR / "raw")

    if not passed:
        print("No signals passed filter.")
        return

    # Phase 3: Analyze
    weight_mode = args.mode if args.mode in ("default", "info_broker", "traffic_arb") else "default"
    print(f"\nAnalyzing ({weight_mode} mode)...")
    analyzed = analyze_signals(passed, mode=weight_mode)

    # Phase 4: Generate brief
    print("Generating brief...")
    brief_md = format_brief(analyzed, len(all_signals), len(passed))

    briefs_dir = PROJECT_DIR / "briefs"
    briefs_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    brief_path = briefs_dir / f"brief_{date_str}.md"
    with open(brief_path, "w", encoding="utf-8") as f:
        f.write(brief_md)

    # Save analyzed JSON
    save_analyzed_signals(analyzed, PROJECT_DIR / "raw")

    high = high_priority(analyzed)
    print(f"\nDone. Brief: {brief_path}")
    print(f"Signals: {len(all_signals)} → filtered {len(passed)} → analyzed {len(analyzed)} → high priority {len(high)}")


def main():
    parser = argparse.ArgumentParser(description="Industry Radar — Arbitrage Signal Engine")
    parser.add_argument("--dry-run", action="store_true", help="Collect only, skip LLM")
    parser.add_argument("--source", type=str, help="Comma-separated source keys (e.g. github,36kr)")
    parser.add_argument("--mode", type=str, default="default",
                        help="Weight mode: default/info_broker/traffic_arb, or 'quick' for 3 fast sources")

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
