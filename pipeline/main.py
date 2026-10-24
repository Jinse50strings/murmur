from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import ROOT, load_config, load_env
from .llm import apply_fallback, enrich_with_llm
from .output import load_recent_archive_papers, write_outputs
from .relevance import dedupe, prefilter, rule_score
from .sources import fetch_arxiv, fetch_openalex


def load_seen(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    ids = payload.get("ids")
    return ids if isinstance(ids, dict) else {}


def save_seen(path: Path, seen: dict[str, str], today: str, keep_days: int = 120) -> None:
    cutoff = (date.fromisoformat(today) - timedelta(days=keep_days)).isoformat()
    pruned = {key: value for key, value in seen.items() if value >= cutoff}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"updated_at": today, "ids": pruned}, ensure_ascii=False, indent=0),
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Murmur daily paper digest pipeline")
    parser.add_argument("--no-llm", action="store_true", help="skip DeepSeek, use rule-based fallback")
    parser.add_argument("--top", type=int, default=None, help="number of papers in today's feed")
    parser.add_argument("--limit", type=int, default=None, help="cap number of LLM candidates")
    parser.add_argument("--out", default=str(ROOT / "docs"), help="output directory")
    parser.add_argument("--data", default=str(ROOT / "data"), help="state directory")
    parser.add_argument("--no-backfill", action="store_true", help="do not fill quiet days from archives")
    parser.add_argument("--ignore-seen", action="store_true", help="ignore data/seen.json for this run")
    parser.add_argument("--no-seen-update", action="store_true", help="do not write seen state after the run")
    parser.add_argument("--require-llm", action="store_true", help="fail if DeepSeek key is missing or all calls fail")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    load_env()
    cfg = load_config()
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    today = now.date().isoformat()
    out_dir = Path(args.out)
    data_dir = Path(args.data)

    collected = []
    source_counts: dict[str, int] = {}
    errors = 0
    for name, fetcher in (("arxiv", fetch_arxiv), ("openalex", fetch_openalex)):
        try:
            fetched = fetcher(cfg)
            source_counts[name] = len(fetched)
            collected.extend(fetched)
            print(f"[{name}] fetched {len(fetched)}", flush=True)
        except Exception as exc:  # noqa: BLE001
            source_counts[name] = 0
            errors += 1
            print(f"[{name}] ERROR: {exc}", flush=True)

    if errors == len(source_counts):
        print("[fatal] every source failed", flush=True)
        return 1

    collected.sort(key=lambda paper: (paper.published, paper.id), reverse=True)
    unique = dedupe(collected)
    print(f"[dedupe] {len(unique)} unique (from {len(collected)})", flush=True)

    seen = load_seen(data_dir / "seen.json")
    fresh = unique if args.ignore_seen else [paper for paper in unique if paper.id not in seen]
    print(f"[seen] {len(fresh)} new (dropped {len(unique) - len(fresh)})", flush=True)

    candidates = [paper for paper in fresh if prefilter(paper, cfg)]
    for paper in candidates:
        paper.rule_score = rule_score(paper, cfg)
    candidates.sort(key=lambda paper: (paper.rule_score, paper.published), reverse=True)
    limit = args.limit or int(cfg["filter"]["max_candidates"])
    candidates = candidates[:limit]
    print(f"[filter] {len(candidates)} candidates", flush=True)

    feed_path = out_dir / "feed.json"
    if not candidates and feed_path.exists():
        try:
            existing = json.loads(feed_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
        if existing.get("date") == today and existing.get("papers"):
            print("[skip] no new candidates and today's feed exists; keeping it", flush=True)
            return 0

    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    llm_enabled = bool(api_key) and not args.no_llm
    if args.require_llm and not llm_enabled:
        print("[fatal] LLM required but DEEPSEEK_API_KEY is missing or empty", flush=True)
        return 1
    llm_failures = 0
    if llm_enabled:
        stats = enrich_with_llm(candidates, cfg, api_key)
        llm_failures = stats["failures"]
        print(
            f"[llm] batches={stats['batches']} failures={stats['failures']} "
            f"tokens_in={stats['prompt_tokens']} tokens_out={stats['completion_tokens']}",
            flush=True,
        )
        if stats["batches"] > 0 and stats["failures"] == stats["batches"]:
            print("[fatal] every LLM batch failed; aborting before writing", flush=True)
            return 1
    else:
        reason = "--no-llm" if args.no_llm else "DEEPSEEK_API_KEY missing"
        print(f"[llm] rule-based fallback ({reason})", flush=True)
        for paper in candidates:
            apply_fallback(paper)

    top_n = args.top or int(cfg["app"]["top_n"])
    min_score = float(cfg["filter"]["min_score"])
    ranked = sorted(candidates, key=lambda paper: (paper.score, paper.published), reverse=True)
    selected = [paper for paper in ranked if paper.score >= min_score][:top_n]

    if not args.no_backfill and len(selected) < 5:
        need = min(int(cfg["app"]["backfill_max"]), 5 - len(selected))
        if need > 0:
            existing = {paper.id for paper in selected}
            pool = load_recent_archive_papers(out_dir, today)
            pool.sort(key=lambda paper: (paper.score, paper.published), reverse=True)
            for paper in pool:
                if need <= 0:
                    break
                if paper.id in existing or paper.score < min_score:
                    continue
                selected.append(paper)
                existing.add(paper.id)
                need -= 1

    counts = {
        "sources": source_counts,
        "unique": len(unique),
        "new": len(fresh),
        "candidates": len(candidates),
        "selected": len(selected),
        "fresh_selected": sum(1 for paper in selected if not paper.backfill_date),
        "errors": errors,
    }
    paths = write_outputs(selected, cfg, out_dir, now, counts)

    if llm_enabled and not args.no_seen_update and llm_failures == 0:
        seen.update({paper.id: today for paper in candidates})
        save_seen(data_dir / "seen.json", seen, today)
    else:
        print("[seen] skipped update", flush=True)

    print(f"[done] {len(selected)} selected -> {paths['feed']}", flush=True)
    for index, paper in enumerate(selected, start=1):
        marker = f" (backfill {paper.backfill_date})" if paper.backfill_date else ""
        print(f"  {index:02d}. [{paper.score:.1f}] {paper.title[:90]}{marker}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
