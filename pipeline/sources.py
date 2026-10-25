from __future__ import annotations

import html as html_lib
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests

from .models import Paper

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
USER_AGENT = "Murmur/0.1 (daily digest; +https://github.com/Jinse50strings/murmur)"
DC_NS = "{http://purl.org/dc/elements/1.1/}"


def _user_agent() -> str:
    contact = os.environ.get("ARXIV_CONTACT", "").strip()
    if contact:
        return f"{USER_AGENT} (mailto:{contact})"
    return USER_AGENT


def _get(
    url: str,
    params: dict[str, Any],
    timeout: int = 90,
    attempts: int = 4,
    backoff: tuple[int, ...] = (2, 5, 10),
) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(
                url,
                params=params,
                headers={"User-Agent": _user_agent()},
                timeout=timeout,
            )
            if response.status_code == 429:
                wait = backoff[min(attempt, len(backoff) - 1)]
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait = int(float(retry_after))
                    except (TypeError, ValueError):
                        pass
                wait = max(3, min(wait, 300))
                last_error = requests.HTTPError("HTTP 429")
                if attempt < attempts - 1:
                    print(f"[http] 429 from {url}; waiting {wait}s", flush=True)
                    time.sleep(wait)
                    continue
                break
            if response.status_code >= 500:
                raise requests.HTTPError(f"HTTP {response.status_code}")
            response.raise_for_status()
            return response
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(backoff[min(attempt, len(backoff) - 1)])
    raise RuntimeError(f"request failed: {url}: {last_error}")


def _fetch_arxiv_api(cfg: dict) -> list[Paper]:
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
    response = _get(
        "https://export.arxiv.org/api/query",
        params,
        attempts=3,
        backoff=(15, 45),
    )
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


def _parse_rss_item(item: ET.Element, category: str) -> Paper | None:
    title = html_lib.unescape(" ".join((item.findtext("title") or "").split()))
    link = (item.findtext("link") or "").strip()
    if not title or "/abs/" not in link:
        return None
    short_id = re.sub(r"v\d+$", "", link.split("/abs/")[-1].split("?")[0].split("#")[0])
    if not short_id:
        return None

    raw_description = item.findtext("description") or ""
    text = html_lib.unescape(re.sub(r"<[^>]+>", " ", raw_description))
    text = " ".join(text.split())
    abstract_match = re.search(r"Abstract:\s*(.*)", text, re.I | re.S)
    abstract = abstract_match.group(1).strip() if abstract_match else text
    if not abstract:
        return None

    authors = [
        creator.text.strip()
        for creator in item.findall(f"{DC_NS}creator")
        if creator.text and creator.text.strip()
    ]
    if not authors:
        authors_match = re.search(r"Authors:\s*(.*?)\s*(?:Abstract:|$)", text, re.I | re.S)
        if authors_match:
            authors = [
                name.strip()
                for name in re.split(r"[,;]", authors_match.group(1))
                if name.strip()
            ]

    categories = [
        category_el.text.strip()
        for category_el in item.findall("category")
        if category_el.text and category_el.text.strip()
    ]
    if category not in categories:
        categories.append(category)

    published = ""
    pub_date = item.findtext("pubDate")
    if pub_date:
        try:
            published = parsedate_to_datetime(pub_date).date().isoformat()
        except (TypeError, ValueError):
            pass
    if not published:
        published = datetime.now(timezone.utc).date().isoformat()

    return Paper(
        id=f"arxiv:{short_id}",
        source="arxiv",
        title=title,
        authors=authors,
        abstract=abstract,
        url=f"https://arxiv.org/abs/{short_id}",
        pdf_url=f"https://arxiv.org/pdf/{short_id}",
        doi=(item.findtext(f"{ARXIV_NS}doi") or "").strip(),
        venue="arXiv",
        published=published,
        categories=categories,
    )


def _fetch_arxiv_rss(cfg: dict) -> list[Paper]:
    by_id: dict[str, Paper] = {}
    for category in cfg["arxiv"]["categories"]:
        url = f"https://rss.arxiv.org/rss/{category}"
        try:
            response = _get(url, {}, timeout=60, attempts=3, backoff=(5, 15))
            root = ET.fromstring(response.content)
            count = 0
            for item in root.iter("item"):
                paper = _parse_rss_item(item, category)
                if paper and paper.id not in by_id:
                    by_id[paper.id] = paper
                    count += 1
            print(f"[arxiv-rss] {category}: {count}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[arxiv-rss] {category} failed: {exc}", flush=True)
        time.sleep(1.2)

    papers = list(by_id.values())
    papers.sort(key=lambda paper: paper.published, reverse=True)
    return papers


def fetch_arxiv(cfg: dict) -> list[Paper]:
    try:
        return _fetch_arxiv_api(cfg)
    except Exception as exc:  # noqa: BLE001
        print(f"[arxiv] API failed: {exc}; falling back to RSS", flush=True)
        papers = _fetch_arxiv_rss(cfg)
        print(f"[arxiv] RSS fallback fetched {len(papers)}", flush=True)
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
