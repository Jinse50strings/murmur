from __future__ import annotations

import dataclasses
from dataclasses import asdict, dataclass, field


@dataclass
class Paper:
    id: str
    source: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    published: str
    venue: str
    categories: list[str] = field(default_factory=list)
    pdf_url: str = ""
    doi: str = ""
    citations: int = 0
    rule_score: float = 0.0
    score: float = 0.0
    tldr_zh: str = ""
    tldr: str = ""
    tags: list[str] = field(default_factory=list)
    reason: str = ""
    backfill_date: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Paper":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})
