from __future__ import annotations

import re

from .models import Paper

_SUFFIX = r"(?:s|es|ing|ed)?"


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    text_l = text.lower()
    hits: list[str] = []
    for keyword in keywords:
        kw = keyword.lower()
        if " " in kw:
            if kw in text_l:
                hits.append(keyword)
        elif re.search(rf"\b{re.escape(kw)}{_SUFFIX}\b", text_l):
            hits.append(keyword)
    return hits


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def prefilter(paper: Paper, cfg: dict) -> bool:
    fcfg = cfg["filter"]
    acfg = cfg["arxiv"]
    categories = {c for c in paper.categories if c}
    core = set(acfg["core_categories"])
    gated = set(acfg["gated_categories"])
    text = f"{paper.title}\n{paper.abstract}"

    if keyword_hits(text, fcfg.get("negative_keywords", [])) and not (categories & core):
        return False

    if categories & core:
        return True
    if categories & gated:
        return bool(keyword_hits(text, fcfg["keywords"]))
    if paper.source == "openalex":
        broad = {j["name"] for j in cfg["openalex"]["journals"] if j.get("broad")}
        if paper.venue in broad:
            return bool(keyword_hits(text, fcfg["keywords"]))
        return True
    return False


def rule_score(paper: Paper, cfg: dict) -> float:
    fcfg = cfg["filter"]
    acfg = cfg["arxiv"]
    categories = {c for c in paper.categories if c}
    text = f"{paper.title}\n{paper.abstract}"
    hits = keyword_hits(text, fcfg["keywords"])
    title_hits = keyword_hits(paper.title, fcfg["keywords"])

    score = 3.0
    if categories & set(acfg["core_categories"]):
        score += 2.0
    if paper.source == "openalex":
        score += 0.5
    score += min(3.0, 0.7 * len(hits))
    if title_hits:
        score += 1.0
    if keyword_hits(text, ["social", "society", "sociological", "network"]):
        score += 0.5
    return round(min(10.0, score), 2)


def dedupe(papers: list[Paper]) -> list[Paper]:
    seen_dois: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[Paper] = []
    for paper in papers:
        doi = (paper.doi or "").lower().replace("https://doi.org/", "").strip()
        title_key = normalize_title(paper.title)
        if doi and doi in seen_dois:
            continue
        if title_key and title_key in seen_titles:
            continue
        if doi:
            seen_dois.add(doi)
        if title_key:
            seen_titles.add(title_key)
        unique.append(paper)
    return unique
