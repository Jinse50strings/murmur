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
<link rel="icon" href="icon.png" type="image/png">
<link rel="apple-touch-icon" href="icon.png">
<style>
:root {
  color-scheme: light dark;
  --bg: #f2f3f0;
  --fg: #121917;
  --muted: #5b6864;
  --faint: #8b9692;
  --card: #fbfcfa;
  --line: #d9dfda;
  --line-strong: #bcc7c1;
  --accent: #0f766e;
  --accent-soft: rgba(15, 118, 110, 0.10);
  --dot: rgba(18, 25, 23, 0.05);
  --glow: rgba(15, 118, 110, 0.06);
  --mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  --serif: ui-serif, "New York", "Songti SC", "Noto Serif SC", Georgia, serif;
  --sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Noto Sans SC", sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #090d0e;
    --fg: #e6eeeb;
    --muted: #8b9a96;
    --faint: #5f6e6a;
    --card: #0e1415;
    --line: #1d2725;
    --line-strong: #2d3a37;
    --accent: #5bd6c8;
    --accent-soft: rgba(91, 214, 200, 0.10);
    --dot: rgba(230, 238, 235, 0.045);
    --glow: rgba(91, 214, 200, 0.07);
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background-color: var(--bg);
  background-image:
    radial-gradient(ellipse 55% 38% at 82% -8%, var(--glow), transparent 70%),
    radial-gradient(circle at 1px 1px, var(--dot) 1px, transparent 0);
  background-size: auto, 24px 24px;
  color: var(--fg);
  font-family: var(--sans);
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}
::selection { background: var(--accent-soft); color: var(--fg); }
a { color: inherit; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; }
.wrap { max-width: 820px; margin: 0 auto; padding: 46px 24px 76px; }
.hero { position: relative; border-bottom: 1px solid var(--line); }
.topline { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.brand {
  display: inline-flex; align-items: center; gap: 9px;
  font-family: var(--mono); font-size: 12px; font-weight: 600;
  letter-spacing: 0.32em; text-transform: uppercase;
}
.brand svg { width: 17px; height: 17px; color: var(--accent); }
.tagline {
  font-family: var(--mono); font-size: 9px; letter-spacing: 0.16em;
  text-transform: uppercase; color: var(--faint);
}
.hero-main { position: relative; padding: 28px 0 24px; }
.eyebrow {
  font-family: var(--mono); font-size: 9.5px; letter-spacing: 0.22em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 12px;
}
h1 {
  font-family: var(--serif); font-size: 38px; font-weight: 600;
  line-height: 1.08; letter-spacing: -0.015em; margin: 0 0 10px;
}
.intro { color: var(--muted); font-size: 13.5px; margin: 0; max-width: 46ch; }
.meta-strip {
  display: flex; gap: 16px; flex-wrap: wrap; margin-top: 18px;
  font-family: var(--mono); font-size: 9.5px; letter-spacing: 0.08em;
  color: var(--faint);
}
.meta-strip span::before { content: "["; color: var(--line-strong); margin-right: 5px; }
.meta-strip span::after { content: "]"; color: var(--line-strong); margin-left: 5px; }
.meta-link {
  appearance: none; border: 0; background: transparent; padding: 0;
  font: inherit; letter-spacing: inherit; color: var(--accent);
  cursor: pointer;
}
.meta-link::before { content: "["; color: var(--line-strong); margin-right: 5px; }
.meta-link::after { content: "]"; color: var(--line-strong); margin-left: 5px; }
.meta-link:hover, .meta-link[aria-expanded="true"] { color: var(--fg); }
.rules-panel {
  margin: 16px 0 2px; padding: 14px 18px;
  border: 1px solid var(--line); border-left: 2px solid var(--accent);
  border-radius: 4px; background: var(--card);
}
.rules-panel[hidden] { display: none; }
.rule-row {
  display: grid; grid-template-columns: 64px 1fr; gap: 14px;
  padding: 7px 0; border-top: 1px solid var(--line);
}
.rule-row:first-child { border-top: 0; padding-top: 0; }
.rule-row:last-child { padding-bottom: 0; }
.rule-key {
  font-family: var(--mono); font-size: 9.5px; letter-spacing: 0.05em;
  color: var(--accent); padding-top: 2px; white-space: nowrap;
}
.rule-row p { margin: 0; font-size: 12px; line-height: 1.7; color: var(--muted); }
.rule-text p { margin: 0; font-size: 12px; line-height: 1.7; color: var(--muted); }
.journal-list { margin-top: 4px; }
.journal-list summary {
  display: inline-block; cursor: pointer; list-style: none;
  font-family: var(--mono); font-size: 10px; color: var(--accent);
  text-decoration: underline; text-underline-offset: 2px;
}
.journal-list summary::-webkit-details-marker { display: none; }
.journal-list span {
  display: block; margin-top: 5px; font-size: 11.5px;
  line-height: 1.7; color: var(--muted);
}
.rule-row b { color: var(--fg); font-weight: 600; }
.net {
  position: absolute; top: 10px; right: -10px; width: 310px; height: 160px;
  color: var(--line-strong); opacity: 0.64; pointer-events: none;
}
.net .edge { fill: none; stroke: currentColor; stroke-width: 0.7; }
.net .node { fill: currentColor; }
.net .accent { fill: var(--accent); }
.net .halo { fill: none; stroke: var(--accent); opacity: 0.45; }
.view-switch { display: flex; gap: 28px; align-items: flex-end; position: relative; }
.view-button {
  appearance: none; border: 0; border-bottom: 1px solid transparent;
  background: transparent; color: var(--muted); cursor: pointer;
  padding: 13px 0 12px; margin-bottom: -1px;
  font-family: var(--mono); font-size: 10.5px; letter-spacing: 0.12em;
  text-transform: uppercase;
}
.view-button:hover { color: var(--fg); }
.view-button.is-active { color: var(--fg); border-bottom-color: var(--accent); }
.view-count { margin-left: 7px; font-size: 9px; color: var(--accent); }
.view-count::before { content: "["; color: var(--line-strong); margin-right: 3px; }
.view-count::after { content: "]"; color: var(--line-strong); margin-left: 3px; }
.view-count:empty { display: none; }
main { padding-top: 18px; }
.card {
  position: relative;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 22px 24px 18px;
  margin: 0 0 16px 26px;
  transition: border-color 0.18s ease;
}
.card:hover { border-color: var(--line-strong); }
.card::before {
  content: ""; position: absolute; left: -20px; top: 26px;
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--card); border: 1.5px solid var(--accent);
  box-shadow: 0 0 0 4px var(--bg);
}
.card::after {
  content: ""; position: absolute; left: -16.5px; top: 37px; bottom: -25px;
  width: 1px; background: var(--line);
}
.card:last-child::after { display: none; }
.card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 11px; }
.head-right { display: flex; align-items: center; gap: 10px; margin-left: auto; }
.rank {
  font-family: var(--mono); font-size: 10px; letter-spacing: 0.12em;
  color: var(--faint); text-transform: uppercase;
}
.score { font-family: var(--mono); font-size: 9.5px; color: var(--muted); white-space: nowrap; }
.score-label {
  font-family: var(--sans); font-size: 9px; letter-spacing: 0.02em;
  color: var(--muted); margin-right: 4px;
}
.bookmark {
  display: inline-flex; align-items: center; justify-content: center;
  width: 30px; height: 30px; margin: -5px -6px -5px 0; padding: 6px;
  border: 0; border-radius: 4px; background: transparent;
  color: var(--faint); cursor: pointer;
}
.bookmark:hover { color: var(--accent); background: var(--accent-soft); }
.bookmark svg {
  width: 17px; height: 17px; fill: none; stroke: currentColor;
  stroke-width: 1.5; stroke-linejoin: round;
}
.bookmark[aria-pressed="true"] { color: var(--accent); }
.bookmark[aria-pressed="true"] svg { fill: currentColor; }
.badge {
  font-family: var(--mono); font-size: 8.5px; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--accent);
  border: 1px solid var(--accent-soft); border-radius: 3px;
  padding: 2px 6px; margin-left: 8px; opacity: 0.9;
}
.card h2 {
  font-family: var(--serif); font-size: 21px; font-weight: 600;
  line-height: 1.36; letter-spacing: -0.005em; margin: 0 0 10px;
}
.card h2 a { text-decoration: none; }
.card h2 a:hover { color: var(--accent); }
.tldr { font-size: 14px; line-height: 1.7; margin: 0 0 14px; color: var(--muted); max-width: 64ch; }
.meta {
  font-family: var(--mono); font-size: 9.5px; letter-spacing: 0.03em;
  color: var(--faint); margin: 0 0 12px;
}
.tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 13px; }
.tag {
  font-family: var(--mono); font-size: 9.5px; color: var(--muted);
  border: 1px solid var(--line); border-radius: 3px; padding: 1px 6px;
}
.links {
  font-family: var(--mono); font-size: 10px; letter-spacing: 0.04em;
  text-transform: uppercase;
}
.links a { color: var(--accent); text-decoration: none; margin-right: 16px; }
.links a::after { content: " ↗"; font-size: 9px; }
.links a:hover { text-decoration: underline; }
footer {
  display: flex; flex-wrap: wrap; justify-content: space-between; gap: 18px;
  border-top: 1px solid var(--line); margin-top: 40px; padding-top: 18px;
  font-family: var(--mono); font-size: 9.5px; letter-spacing: 0.03em;
  color: var(--faint);
}
.footer-links { display: flex; gap: 14px; flex-wrap: wrap; }
.footer-links a { color: var(--muted); text-decoration: none; }
.footer-links a:hover { color: var(--accent); }
.footer-links span { color: var(--line-strong); }
.disclaimer { flex-basis: 100%; margin: 0; color: var(--faint); max-width: 56ch; line-height: 1.7; }
.empty {
  font-family: var(--mono); font-size: 10px; letter-spacing: 0.04em;
  color: var(--faint); text-align: center; padding: 52px 18px;
  border: 1px dashed var(--line-strong); border-radius: 9px;
  margin: 0 0 0 26px;
}
.favorites-toolbar {
  display: flex; justify-content: space-between; align-items: flex-end;
  gap: 16px; padding: 4px 0 18px; margin-bottom: 22px;
  border-bottom: 1px solid var(--line);
}
.favorites-toolbar h2 {
  font-family: var(--serif); font-size: 26px; font-weight: 600;
  margin: 4px 0; letter-spacing: -0.01em;
}
.favorites-sub {
  font-family: var(--mono); font-size: 9.5px; letter-spacing: 0.03em;
  color: var(--faint); margin: 0;
}
.ghost-button {
  border: 1px solid var(--line-strong); background: transparent; color: var(--muted);
  font-family: var(--mono); font-size: 9.5px; letter-spacing: 0.1em;
  text-transform: uppercase; padding: 8px 11px; border-radius: 4px;
  cursor: pointer; white-space: nowrap;
}
.ghost-button:hover { border-color: var(--accent); color: var(--accent); }
#today-view[hidden], #favorites-view[hidden] { display: none !important; }
@media (max-width: 720px) {
  .net { display: none; }
}
@media (max-width: 520px) {
  .wrap { padding: 36px 18px 64px; }
  .brand { font-size: 11px; }
  .tagline { display: none; }
  h1 { font-size: 31px; }
  .rules-panel { padding: 12px 14px; }
  .rule-row { grid-template-columns: 52px 1fr; gap: 10px; }
  .card { margin-left: 18px; padding: 18px 16px 14px; }
  .card::before { left: -15px; top: 22px; }
  .card::after { left: -11.5px; top: 33px; }
  .card h2 { font-size: 18px; }
  .tldr { font-size: 13.5px; }
  .empty { margin-left: 18px; }
  .favorites-toolbar { flex-direction: column; align-items: stretch; }
  .ghost-button { align-self: flex-start; }
}
</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <div class="topline">
      <span class="brand">
        <svg viewBox="0 0 20 20" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.1"><path d="M4 14.5 8 5.5l4.5 6 3.5-4"/><path d="M12.5 11.5 16 15"/></g><g fill="currentColor"><circle cx="4" cy="14.5" r="1.4"/><circle cx="8" cy="5.5" r="1.4"/><circle cx="12.5" cy="11.5" r="1.4"/><circle cx="16" cy="7.5" r="1.2"/><circle cx="16" cy="15" r="1.2"/></g></svg>
        Murmur
      </span>
      <span class="tagline">Complex networks / computational social science</span>
    </div>
    <div class="hero-main">
      <div class="eyebrow">Daily digest · __DATE_ISO__</div>
      <h1>__DATE_ZH__</h1>
      <p class="intro">每天从 arXiv 与核心期刊中筛选社会网络、复杂网络与计算社会科学前沿。</p>
      <div class="meta-strip">
        <span>N = __COUNT__</span>
        <span>__SOURCE_LABEL__</span>
        <span>更新 00:30 CST</span>
        <button class="meta-link" id="rules-toggle" type="button" aria-expanded="false" aria-controls="rules-panel">评分规则</button>
      </div>
      <div class="rules-panel" id="rules-panel" hidden>
        <div class="rule-row"><span class="rule-key">0–10</span><p>AI 相关性评分：衡量论文与「复杂网络 / 计算社会科学」的接近程度，不代表论文质量、引用量或作者水平。</p></div>
        <div class="rule-row"><span class="rule-key">分数段</span><p><b>9–10</b> 核心问题、方法或重要发现；<b>7–8</b> 明确相关；<b>5–6</b> 边缘相关；<b>0–4</b> 基本不相关。</p></div>
        <div class="rule-row"><span class="rule-key">入选</span><p>每天按分数排序取前 10；低于 5.0 不入选。新论文不足时，从最近 7 天归档补足「往期精选」。</p></div>
        <div class="rule-row"><span class="rule-key">来源</span><div class="rule-text">
          <p>arXiv（近 72 小时）：__ARXIV_CATEGORIES__。</p>
          <p>OpenAlex 期刊（__JOURNAL_COUNT__ 本）：</p>
          <details class="journal-list"><summary>查看期刊列表</summary><span>__JOURNAL_LIST__</span></details>
        </div></div>
        <div class="rule-row"><span class="rule-key">说明</span><p>评分与中文导读由 DeepSeek 生成，仅作研究线索，请以论文原文为准。</p></div>
      </div>
      <svg class="net" viewBox="0 0 320 160" aria-hidden="true">
        <g class="edge">
          <path d="M16 110 52 42 88 84 126 30 160 72 196 40 232 94 268 48 300 110"/>
          <path d="M16 110 88 84M88 84 160 72M160 72 232 94M232 94 300 110"/>
          <path d="M118 128 88 84M118 128 160 72M118 128 176 132M176 132 160 72M176 132 220 146M220 146 232 94M282 144 300 110M64 142 16 110M64 142 118 128M246 18 196 40M246 18 268 48"/>
        </g>
        <g class="node">
          <circle cx="16" cy="110" r="2"/><circle cx="52" cy="42" r="2"/>
          <circle cx="88" cy="84" r="2"/><circle cx="126" cy="30" r="2"/>
          <circle cx="160" cy="72" r="2"/><circle cx="196" cy="40" r="2"/>
          <circle cx="232" cy="94" r="2"/><circle cx="268" cy="48" r="2"/>
          <circle cx="300" cy="110" r="2"/><circle cx="118" cy="128" r="2"/>
          <circle cx="176" cy="132" r="2"/><circle cx="220" cy="146" r="2"/>
          <circle cx="282" cy="144" r="2"/><circle cx="64" cy="142" r="2"/>
          <circle cx="246" cy="18" r="1.6"/>
        </g>
        <g class="accent">
          <circle cx="160" cy="72" r="2.8"/>
          <circle class="halo" cx="160" cy="72" r="8"/>
        </g>
      </svg>
    </div>
    <div class="view-switch" role="tablist" aria-label="视图">
      <button class="view-button is-active" type="button" data-view="today" role="tab" aria-selected="true">今日</button>
      <button class="view-button" type="button" data-view="favorites" role="tab" aria-selected="false">收藏<span class="view-count" id="fav-count-badge"></span></button>
    </div>
  </header>
  <main id="today-view">
    __CARDS__
  </main>
  <section id="favorites-view" hidden aria-label="我的收藏">
    <div class="favorites-toolbar">
      <div>
        <div class="eyebrow">Collection / local</div>
        <h2>我的收藏</h2>
        <p class="favorites-sub">保存在当前浏览器 · <span id="favorites-count"></span>不上传服务器</p>
      </div>
      <button class="ghost-button" id="export-favorites" type="button">导出 JSON</button>
    </div>
    <div id="favorites-list"></div>
    <p class="empty" id="favorites-empty" hidden>还没有收藏。点击论文卡片右上角的书签即可保存。</p>
  </section>
  <footer>
    <div class="footer-links">
      <a href="feed.json">JSON Feed</a>
      <span>/</span>
      <a href="archive/index.json">Archive</a>
      <span>/</span>
      <span>__GENERATED__</span>
    </div>
    <p class="disclaimer">内容由 AI 辅助筛选和摘要，仅作研究线索，请以论文原文为准。</p>
  </footer>
</div>
<script id="feed-data" type="application/json">__FEED_JSON__</script>
<script>__SCRIPT__</script>
</body>
</html>
"""

CARD_TEMPLATE = """<article class="card" data-paper-id="__PAPER_ID__">
  <div class="card-head">
    <span class="rank">__RANK__</span>
    <div class="head-right">
      <span>__BADGES__</span>
      __SCORE__
      <button class="bookmark" type="button" data-bookmark="__PAPER_ID__" aria-pressed="false" aria-label="收藏" title="收藏">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.5 3.5h11A1.5 1.5 0 0 1 19 5v15.2a.8.8 0 0 1-1.25.66L12 16.9l-5.75 3.96A.8.8 0 0 1 5 20.2V5a1.5 1.5 0 0 1 1.5-1.5Z"/></svg>
      </button>
    </div>
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

FAVORITES_SCRIPT = """
(function () {
  "use strict";

  var STORAGE_KEY = "murmur.favorites.v1";
  var feedNode = document.getElementById("feed-data");
  var feed = [];
  try {
    feed = JSON.parse(feedNode.textContent || "[]");
  } catch (error) {
    feed = [];
  }

  var paperById = Object.create(null);
  feed.forEach(function (paper) {
    if (paper && paper.id) paperById[paper.id] = paper;
  });

  var todayView = document.getElementById("today-view");
  var favoritesView = document.getElementById("favorites-view");
  var favoritesList = document.getElementById("favorites-list");
  var favoritesEmpty = document.getElementById("favorites-empty");
  var countBadge = document.getElementById("fav-count-badge");
  var countText = document.getElementById("favorites-count");
  var viewButtons = Array.prototype.slice.call(document.querySelectorAll("[data-view]"));

  function loadFavorites() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      var parsed = raw ? JSON.parse(raw) : {};
      var clean = Object.create(null);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        Object.keys(parsed).forEach(function (key) {
          var value = parsed[key];
          if (value && typeof value === "object" && value.id) clean[key] = value;
        });
      }
      return clean;
    } catch (error) {
      return Object.create(null);
    }
  }

  var favorites = loadFavorites();

  function saveFavorites() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
    } catch (error) {
      /* storage unavailable: keep the in-memory state */
    }
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function safeUrl(value) {
    try {
      var url = new URL(String(value || ""), window.location.href);
      return url.protocol === "http:" || url.protocol === "https:" ? url.href : "";
    } catch (error) {
      return "";
    }
  }

  function shortDate(iso) {
    var match = /^(\\d{4})-(\\d{2})-(\\d{2})/.exec(String(iso || ""));
    if (!match) return String(iso || "");
    return parseInt(match[2], 10) + "月" + parseInt(match[3], 10) + "日";
  }

  function summaryOf(paper) {
    if (paper.tldr_zh) return paper.tldr_zh;
    if (paper.tldr) return paper.tldr;
    var text = String(paper.abstract || "");
    return text.length > 220 ? text.slice(0, 220) + "…" : text;
  }

  function authorsOf(paper) {
    var authors = Array.isArray(paper.authors) ? paper.authors : [];
    if (!authors.length) return "";
    return authors.length <= 3
      ? authors.join("、")
      : authors.slice(0, 3).join("、") + " 等";
  }

  function bookmarkButton(id, pressed) {
    var label = pressed ? "取消收藏" : "收藏";
    return (
      '<button class="bookmark" type="button" data-bookmark="' + escapeHtml(id) + '" ' +
      'aria-pressed="' + (pressed ? "true" : "false") + '" ' +
      'aria-label="' + label + '" title="' + label + '">' +
      '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.5 3.5h11A1.5 1.5 0 0 1 19 5v15.2a.8.8 0 0 1-1.25.66L12 16.9l-5.75 3.96A.8.8 0 0 1 5 20.2V5a1.5 1.5 0 0 1 1.5-1.5Z"/></svg>' +
      "</button>"
    );
  }

  function favoriteCard(paper) {
    var url = safeUrl(paper.url);
    var pdf = safeUrl(paper.pdf_url);
    var doi = safeUrl(paper.doi);
    var score = Number(paper.score);
    var tags = (Array.isArray(paper.tags) ? paper.tags : [])
      .map(function (tag) { return '<span class="tag">' + escapeHtml(tag) + "</span>"; })
      .join("");
    var meta = [paper.venue, shortDate(paper.published), authorsOf(paper)]
      .filter(Boolean)
      .map(escapeHtml)
      .join(" · ");
    var links = url ? '<a href="' + escapeHtml(url) + '" target="_blank" rel="noopener">原文</a>' : "";
    if (pdf) links += '<a href="' + escapeHtml(pdf) + '" target="_blank" rel="noopener">PDF</a>';
    if (doi) links += '<a href="' + escapeHtml(doi) + '" target="_blank" rel="noopener">DOI</a>';
    var title = url
      ? '<a href="' + escapeHtml(url) + '" target="_blank" rel="noopener">' + escapeHtml(paper.title) + "</a>"
      : escapeHtml(paper.title);
    var scoreHtml = paper.score != null && isFinite(score)
      ? '<span class="score"><span class="score-label">评分</span>' + score.toFixed(1) + "</span>"
      : "";

    return (
      '<article class="card favorite-card" data-paper-id="' + escapeHtml(paper.id) + '">' +
      '<div class="card-head"><span class="rank">Saved</span><div class="head-right">' +
      scoreHtml + bookmarkButton(paper.id, true) + "</div></div>" +
      "<h2>" + title + "</h2>" +
      '<p class="tldr">' + escapeHtml(summaryOf(paper)) + "</p>" +
      '<p class="meta">' + meta + "</p>" +
      (tags ? '<div class="tags">' + tags + "</div>" : "") +
      (links ? '<div class="links">' + links + "</div>" : "") +
      "</article>"
    );
  }

  function favoriteItems() {
    return Object.keys(favorites)
      .map(function (id) { return favorites[id]; })
      .filter(function (paper) { return paper && paper.id; })
      .sort(function (a, b) {
        return String(b.saved_at || "").localeCompare(String(a.saved_at || ""));
      });
  }

  function renderFavorites() {
    var items = favoriteItems();
    countBadge.textContent = items.length ? String(items.length) : "";
    countText.textContent = items.length ? items.length + " 篇 · " : "";
    favoritesList.innerHTML = items.map(favoriteCard).join("");
    favoritesList.hidden = items.length === 0;
    favoritesEmpty.hidden = items.length > 0;
  }

  function updateBookmarkButtons() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-bookmark]"), function (button) {
      var id = button.getAttribute("data-bookmark");
      var active = Boolean(favorites[id]);
      var label = active ? "取消收藏" : "收藏";
      button.setAttribute("aria-pressed", active ? "true" : "false");
      button.setAttribute("aria-label", label);
      button.setAttribute("title", label);
    });
  }

  function toggleFavorite(id) {
    if (!id) return;
    if (favorites[id]) {
      delete favorites[id];
    } else {
      var paper = paperById[id];
      if (!paper) return;
      var copy = {};
      ["id", "title", "authors", "abstract", "url", "venue", "published",
       "pdf_url", "doi", "score", "tldr_zh", "tldr", "tags"].forEach(function (key) {
        if (paper[key] != null) copy[key] = paper[key];
      });
      copy.saved_at = new Date().toISOString();
      favorites[id] = copy;
    }
    saveFavorites();
    renderFavorites();
    updateBookmarkButtons();
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-bookmark]");
    if (!button) return;
    event.preventDefault();
    toggleFavorite(button.getAttribute("data-bookmark"));
  });

  function setView(view) {
    todayView.hidden = view !== "today";
    favoritesView.hidden = view !== "favorites";
    viewButtons.forEach(function (button) {
      var active = button.getAttribute("data-view") === view;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", active ? "true" : "false");
    });
    if (view === "favorites") renderFavorites();
  }

  viewButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      setView(button.getAttribute("data-view"));
    });
  });

  var exportButton = document.getElementById("export-favorites");
  if (exportButton) {
    exportButton.addEventListener("click", function () {
      var blob = new Blob([JSON.stringify(favoriteItems(), null, 2)], { type: "application/json" });
      var link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "murmur-favorites.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(function () { URL.revokeObjectURL(link.href); }, 1000);
    });
  }

  window.addEventListener("storage", function (event) {
    if (event.key !== STORAGE_KEY) return;
    favorites = loadFavorites();
    renderFavorites();
    updateBookmarkButtons();
  });

  var rulesToggle = document.getElementById("rules-toggle");
  var rulesPanel = document.getElementById("rules-panel");
  if (rulesToggle && rulesPanel) {
    rulesToggle.addEventListener("click", function () {
      var expanded = rulesToggle.getAttribute("aria-expanded") === "true";
      rulesToggle.setAttribute("aria-expanded", expanded ? "false" : "true");
      rulesPanel.hidden = expanded;
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !rulesPanel.hidden) {
        rulesPanel.hidden = true;
        rulesToggle.setAttribute("aria-expanded", "false");
        rulesToggle.focus();
      }
    });
  }

  renderFavorites();
  updateBookmarkButtons();
})();
"""



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
        score_html = (
            f'<span class="score"><span class="score-label">评分</span>{paper.score:.1f}</span>'
            if paper.score
            else ""
        )
        card = CARD_TEMPLATE
        replacements = {
            "__RANK__": f"{index:02d}",
            "__PAPER_ID__": html.escape(paper.id),
            "__BADGES__": badges,
            "__SCORE__": score_html,
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


def render_page(papers: list[Paper], now: datetime, cfg: dict | None = None) -> str:
    page = PAGE_TEMPLATE
    feed_json = json.dumps([paper.to_dict() for paper in papers], ensure_ascii=False)
    feed_json = feed_json.replace("<", "\\u003c")

    journals = (cfg or {}).get("openalex", {}).get("journals", [])
    journal_names = [str(j.get("name", "")) for j in journals if j.get("name")]
    journal_count = len(journal_names)
    source_label = f"arXiv + {journal_count} 本期刊" if journal_count else "arXiv + 期刊"
    journal_text = "、".join(journal_names) if journal_names else "—"
    categories = (cfg or {}).get("arxiv", {}).get("categories", [])
    categories_text = "、".join(categories) if categories else "—"

    replacements = {
        "__DATE__": now.date().isoformat(),
        "__DATE_ISO__": now.date().isoformat(),
        "__DATE_ZH__": _format_date_zh(now.date().isoformat()),
        "__COUNT__": str(len(papers)),
        "__SOURCE_LABEL__": source_label,
        "__JOURNAL_COUNT__": str(journal_count),
        "__JOURNAL_LIST__": html.escape(journal_text),
        "__ARXIV_CATEGORIES__": html.escape(categories_text),
        "__CARDS__": _cards_html(papers),
        "__GENERATED__": now.strftime("%Y-%m-%d %H:%M"),
        "__FEED_JSON__": feed_json,
        "__SCRIPT__": FAVORITES_SCRIPT,
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
    page_path.write_text(render_page(papers, now, cfg), encoding="utf-8")

    wechat_path = out_dir / "wechat_draft.html"
    wechat_path.write_text(render_wechat(papers, now, cfg), encoding="utf-8")

    return {
        "feed": feed_path,
        "archive": archive_path,
        "page": page_path,
        "wechat": wechat_path,
    }
