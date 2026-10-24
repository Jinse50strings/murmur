from __future__ import annotations

import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from .models import Paper

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
USER_AGENT = "Murmur/0.1 (daily digest; +https://github.com/Jinse50strings/murmur)"


def _get(url: str, params: dict[str, Any], timeout: int = 90, attempts: int = 4) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
            )
            if response.status_code in {429, 500, 502, 503, 504}:
                raise requests.HTTPError(f"HTTP {response.status_code}")
            response.raise_for_status()
            return response
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"request failed: {url}: {last_error}")


def fetch_arxiv(cfg: dict) -> list[Paper]:
    acfg = cfg["arxiv"]
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=int(acfg["lookback_hours"]))
    date_fmt = "%Y%m%d%H%M"
    categories = " OR ".join(f"cat:{c}" for c in acfg["categories"])
    query = f"({categories}) AND submittedDate:[{start.strftime(date_fmt)} TO {end.strftime(date_fmt)}]"
    params = {
        "search_query": query,
        "start": 0,
        "max_results": int(acfg["max_results"]),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    response = _get("https://export.arxiv.org/api/query", params)
    root = ET.fromstring(response.content)

    papers: list[Paper] = []
    for entry in root.findall(f"{ATOM}entry"):
        raw_id = (entry.findtext(f"{ATOM}id") or "").strip()
        if "/abs/" not in raw_id:
            continue
        short_id = re.sub(r"v\d+$", "", raw_id.split("/abs/")[-1])
        title = " ".join((entry.findtext(f"{ATOM}title") or "").split())
        abstract = " ".join((entry.findtext(f"{ATOM}summary") or "").split())
        if not title or not abstract:
            continue
        authors = []
        for author in entry.findall(f"{ATOM}author"):
            name = (author.findtext(f"{ATOM}name") or "").strip()
            if name:
                authors.append(name)
        categories = [c.get("term") for c in entry.findall(f"{ATOM}category") if c.get("term")]
        pdf_url = f"https://arxiv.org/pdf/{short_id}"
        for link in entry.findall(f"{ATOM}link"):
            if link.get("title") == "pdf" and link.get("href"):
                pdf_url = link.get("href")
        papers.append(
            Paper(
                id=f"arxiv:{short_id}",
                source="arxiv",
                title=title,
                authors=authors,
                abstract=abstract,
                url=f"https://arxiv.org/abs/{short_id}",
                pdf_url=pdf_url,
                doi=(entry.findtext(f"{ARXIV_NS}doi") or "").strip(),
                venue="arXiv",
                published=(entry.findtext(f"{ATOM}published") or "")[:10],
                categories=categories,
            )
        )
    return papers


def _abstract_from_inverted(inverted: dict | None) -> str:
    if not inverted:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indexes in inverted.items():
        for index in indexes:
            positions.append((index, word))
    positions.sort()
    return " ".join(word for _, word in positions)


def _parse_openalex_work(work: dict) -> Paper | None:
    title = " ".join((work.get("title") or work.get("display_name") or "").split())
    abstract = _abstract_from_inverted(work.get("abstract_inverted_index"))
    if len(title) < 8 or len(abstract) < 60:
        return None
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    venue = (source.get("display_name") or "").strip()
    if not venue:
        return None
    doi = (work.get("doi") or "").strip()
    url = doi or primary_location.get("landing_page_url") or (work.get("id") or "")
    openalex_id = (work.get("id") or "").rsplit("/", 1)[-1]
    authors = []
    for authorship in work.get("authorships") or []:
        name = ((authorship.get("author") or {}).get("display_name") or "").strip()
        if name:
            authors.append(name)
    return Paper(
        id=f"openalex:{openalex_id}",
        source="openalex",
        title=title,
        authors=authors,
        abstract=abstract,
        url=url,
        doi=doi,
        venue=venue,
        published=(work.get("publication_date") or work.get("created_date") or "")[:10],
        citations=int(work.get("cited_by_count") or 0),
    )


def fetch_openalex(cfg: dict) -> list[Paper]:
    ocfg = cfg["openalex"]
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=int(ocfg["lookback_days"]))
    issns = "|".join(j["issn"] for j in ocfg["journals"])
    filters = ",".join(
        [
            f"locations.source.issn:{issns}",
            f"from_publication_date:{start_date.isoformat()}",
            "is_paratext:false",
        ]
    )
    params = {
        "filter": filters,
        "per-page": int(ocfg["per_page"]),
        "select": (
            "id,doi,title,display_name,authorships,primary_location,"
            "publication_date,created_date,abstract_inverted_index,cited_by_count"
        ),
    }
    mailto = os.environ.get("OPENALEX_MAILTO", "").strip()
    if mailto:
        params["mailto"] = mailto

    papers: list[Paper] = []
    cursor = "*"
    pages = 0
    while cursor and pages < int(ocfg["max_pages"]):
        params["cursor"] = cursor
        payload = _get("https://api.openalex.org/works", params).json()
        results = payload.get("results") or []
        for work in results:
            paper = _parse_openalex_work(work)
            if paper:
                papers.append(paper)
        cursor = (payload.get("meta") or {}).get("next_cursor")
        pages += 1
        if not results:
            break
    return papers
