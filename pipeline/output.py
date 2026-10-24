from __future__ import annotations

import html
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from .models import Paper

PAGE_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Murmur · __DATE__</title>
<style>
:root {
  color-scheme: light dark;
  --bg: #f7f6f2;
  --fg: #191a1c;
  --muted: #6c6f75;
  --card: #ffffff;
  --line: #e5e1d8;
  --accent: #1f6f64;
  --accent-soft: #e3efec;
  --tagbg: #f0efe9;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #101214;
    --fg: #eceae4;
    --muted: #9a9da3;
    --card: #181b1e;
    --line: #292d31;
    --accent: #7fc4b8;
    --accent-soft: #1b2b29;
    --tagbg: #22262a;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--fg);
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Noto Sans SC", sans-serif;
  line-height: 1.65;
}
.wrap { max-width: 780px; margin: 0 auto; padding: 56px 22px 88px; }
.hero { border-bottom: 1px solid var(--line); padding-bottom: 28px; margin-bottom: 34px; }
.topline { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
.brand { font-size: 34px; font-weight: 750; letter-spacing: -0.5px; }
.tagline { color: var(--muted); font-size: 14px; letter-spacing: 0.2px; }
h1 { font-size: 20px; font-weight: 600; margin: 22px 0 8px; }
.count { color: var(--accent); font-size: 14px; font-weight: 500; margin-left: 12px; }
.intro { color: var(--muted); font-size: 14px; margin: 0; }
.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 24px 26px 20px;
  margin-bottom: 18px;
}
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.rank { font-variant-numeric: tabular-nums; font-size: 13px; color: var(--muted); letter-spacing: 1px; }
.badge {
  font-size: 11px; color: var(--accent); background: var(--accent-soft);
  border-radius: 999px; padding: 3px 9px; margin-left: 8px;
}
.card h2 { font-size: 19px; line-height: 1.4; margin: 0 0 12px; font-weight: 650; }
.card h2 a { color: var(--fg); text-decoration: none; }
.card h2 a:hover { color: var(--accent); }
.tldr { font-size: 15px; margin: 0 0 14px; }
.meta { color: var(--muted); font-size: 12.5px; margin: 0 0 12px; }
.tags { display: flex; flex-wrap: wrap; gap: 7px; margin-bottom: 14px; }
.tag { background: var(--tagbg); color: var(--muted); border-radius: 6px; padding: 2px 8px; font-size: 12px; }
.links { font-size: 13px; }
.links a { color: var(--accent); text-decoration: none; margin-right: 14px; }
.links a:hover { text-decoration: underline; }
footer { border-top: 1px solid var(--line); margin-top: 40px; padding-top: 20px; color: var(--muted); font-size: 12.5px; }
.footer-links { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
.footer-links a { color: var(--accent); text-decoration: none; }
.disclaimer { margin: 4px 0 0; }
.empty { color: var(--muted); text-align: center; padding: 60px 0; }
@media (max-width: 520px) {
  .wrap { padding-top: 40px; }
  .card { padding: 20px 18px 16px; }
  .brand { font-size: 30px; }
}
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <div class="topline">
      <span class="brand">Murmur</span>
      <span class="tagline">复杂网络 · 计算社会科学 · 每日论文</span>
    </div>
    <h1>__DATE_ZH__<span class="count">__COUNT__ 篇</span></h1>
    <p class="intro">每天从 arXiv 与核心期刊中筛选社会网络、复杂网络与计算社会科学前沿。</p>
  </header>
  <main>
    __CARDS__
  </main>
  <footer>
    <div class="footer-links">
      <a href="feed.json">JSON Feed</a>
      <span>·</span>
      <a href="archive/index.json">归档</a>
      <span>·</span>
      <span>生成于 __GENERATED__</span>
    </div>
    <p class="disclaimer">内容由 AI 辅助筛选和摘要，仅作研究线索，请以论文原文为准。</p>
  </footer>
</div>
</body>
</html>
"""

CARD_TEMPLATE = """<article class="card">
  <div class="card-head">
    <span class="rank">__RANK__</span>
    <span>__BADGES__</span>
  </div>
  <h2><a href="__URL__" target="_blank" rel="noopener">__TITLE__</a></h2>
  <p class="tldr">__TLDR__</p>
  <p class="meta">__META__</p>
  <div class="tags">__TAGS__</div>
  <div class="links">
    <a href="__URL__" target="_blank" rel="noopener">原文</a>
    __PDF__
    __DOI__
  </div>
</article>"""


def _format_date_zh(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value).date()
    except ValueError:
        return value
    return f"{parsed.year}年{parsed.month}月{parsed.day}日"


def _authors_text(authors: list[str]) -> str:
    if not authors:
        return ""
    if len(authors) <= 3:
        return ", ".join(authors)
    return ", ".join(authors[:3]) + " 等"


def _summary(paper: Paper) -> str:
    text = paper.tldr_zh or paper.tldr
    if not text:
        text = paper.abstract[:220] + ("…" if len(paper.abstract) > 220 else "")
    return text


def _cards_html(papers: list[Paper]) -> str:
    if not papers:
        return '<p class="empty">今天没有新的论文，明天见。</p>'
    cards = []
    for index, paper in enumerate(papers, start=1):
        badges = ""
        if paper.backfill_date:
            badges += f'<span class="badge">往期精选 · {html.escape(paper.backfill_date[5:])}</span>'
        tags = "".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in paper.tags)
        pdf_link = (
            f'<a href="{html.escape(paper.pdf_url)}" target="_blank" rel="noopener">PDF</a>'
            if paper.pdf_url
            else ""
        )
        doi_link = (
            f'<a href="{html.escape(paper.doi)}" target="_blank" rel="noopener">DOI</a>'
            if paper.doi
            else ""
        )
        meta_parts = [part for part in [paper.venue, paper.published, _authors_text(paper.authors)] if part]
        card = CARD_TEMPLATE
        replacements = {
            "__RANK__": f"{index:02d}",
            "__BADGES__": badges,
            "__URL__": html.escape(paper.url),
            "__TITLE__": html.escape(paper.title),
            "__TLDR__": html.escape(_summary(paper)),
            "__META__": html.escape(" · ".join(meta_parts)),
            "__TAGS__": tags,
            "__PDF__": pdf_link,
            "__DOI__": doi_link,
        }
        for key, value in replacements.items():
            card = card.replace(key, value)
        cards.append(card)
    return "\n".join(cards)


def render_page(papers: list[Paper], now: datetime) -> str:
    page = PAGE_TEMPLATE
    replacements = {
        "__DATE__": now.date().isoformat(),
        "__DATE_ZH__": _format_date_zh(now.date().isoformat()),
        "__COUNT__": str(len(papers)),
        "__CARDS__": _cards_html(papers),
        "__GENERATED__": now.strftime("%Y-%m-%d %H:%M"),
    }
    for key, value in replacements.items():
        page = page.replace(key, value)
    return page


def render_wechat(papers: list[Paper], now: datetime, cfg: dict) -> str:
    top_n = int(cfg["app"]["wechat_top_n"])
    selected = papers[:top_n]
    items = []
    for index, paper in enumerate(selected, start=1):
        summary = _summary(paper)
        badge = "（往期精选）" if paper.backfill_date else ""
        tags = " / ".join(paper.tags)
        venue = paper.venue if paper.venue != "arXiv" else "arXiv 预印本"
        items.append(
            f'<p style="margin:0 0 6px;font-size:15px;font-weight:600;color:#1f6f64;">'
            f"{index:02d}　{html.escape(summary)}{html.escape(badge)}</p>"
            f'<p style="margin:0 0 4px;font-size:14px;color:#333;">{html.escape(paper.title)}</p>'
            f'<p style="margin:0 0 4px;font-size:12px;color:#888;">'
            f"{html.escape(venue)} · {html.escape(paper.published)} · {html.escape(tags)}</p>"
            f'<p style="margin:0 0 18px;font-size:12px;color:#888;">原文：'
            f'<a href="{html.escape(paper.url)}" style="color:#1f6f64;">{html.escape(paper.url)}</a></p>'
        )
    body = "\n".join(items) if items else '<p style="color:#888;">今日无新论文。</p>'
    date_zh = _format_date_zh(now.date().isoformat())
    return f"""<section style="font-size:15px;color:#222;line-height:1.75;">
<p style="margin:0 0 4px;font-size:20px;font-weight:700;color:#1f6f64;">Murmur</p>
<p style="margin:0 0 2px;font-size:13px;color:#666;">复杂网络 · 计算社会科学 · 每日论文</p>
<p style="margin:0 0 18px;font-size:13px;color:#666;">{date_zh} · 共 {len(papers)} 篇</p>
<hr style="border:none;border-top:1px solid #e5e1d8;margin:0 0 18px;">
{body}
<p style="margin:18px 0 0;font-size:12px;color:#999;">由 Murmur 自动生成，AI 辅助摘要，请以原文为准。数据源：arXiv / OpenAlex。</p>
</section>
"""


def load_recent_archive_papers(out_dir: Path, today: str, days: int = 7) -> list[Paper]:
    archive_dir = out_dir / "archive"
    if not archive_dir.exists():
        return []
    base = date.fromisoformat(today)
    papers: list[Paper] = []
    for offset in range(1, days + 1):
        day = (base - timedelta(days=offset)).isoformat()
        path = archive_dir / f"{day}.json"
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for item in payload.get("papers") or []:
            if item.get("backfill_date"):
                continue
            try:
                paper = Paper.from_dict(item)
            except TypeError:
                continue
            paper.backfill_date = day
            papers.append(paper)
    return papers


def _update_manifest(archive_dir: Path, day: str) -> None:
    manifest_path = archive_dir / "index.json"
    dates: list[str] = []
    if manifest_path.exists():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            dates = [str(d) for d in payload.get("dates") or []]
        except (OSError, json.JSONDecodeError):
            dates = []
    dates = [d for d in dates if d != day]
    dates.insert(0, day)
    manifest_path.write_text(
        json.dumps({"dates": dates[:365]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_outputs(
    papers: list[Paper],
    cfg: dict,
    out_dir: Path,
    now: datetime,
    counts: dict,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    day = now.date().isoformat()

    feed = {
        "app": cfg["app"]["name"],
        "version": 1,
        "date": day,
        "generated_at": now.isoformat(timespec="seconds"),
        "count": len(papers),
        "counts": counts,
        "papers": [paper.to_dict() for paper in papers],
    }

    feed_path = out_dir / "feed.json"
    feed_path.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")

    archive_dir = out_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{day}.json"
    archive_path.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")
    _update_manifest(archive_dir, day)

    page_path = out_dir / "index.html"
    page_path.write_text(render_page(papers, now), encoding="utf-8")

    wechat_path = out_dir / "wechat_draft.html"
    wechat_path.write_text(render_wechat(papers, now, cfg), encoding="utf-8")

    return {
        "feed": feed_path,
        "archive": archive_path,
        "page": page_path,
        "wechat": wechat_path,
    }
