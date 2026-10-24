from __future__ import annotations

import json
import re
import time

import requests

from .models import Paper
from .relevance import keyword_hits

SYSTEM_PROMPT = "你是严谨的学术论文筛选助手，只根据标题和摘要判断，不编造内容。"


def _first_sentence(text: str, limit: int = 280) -> str:
    text = text.strip()
    match = re.match(r"(.+?[.!?])(?:\s|$)", text)
    sentence = match.group(1) if match else text
    return sentence[:limit].strip()


def _fallback_tags(paper: Paper) -> list[str]:
    mapping = [
        ("社会网络", ["social network", "tie", "dyad", "homophily", "social capital", "peer effect", "social influence"]),
        ("复杂网络", ["complex network", "network science", "centrality", "community detection", "power law", "percolation", "random graph", "multilayer", "network topology"]),
        ("扩散与传播", ["diffusion", "contagion", "cascade", "information diffusion", "social contagion"]),
        ("舆论与极化", ["polarization", "echo chamber", "misinformation", "disinformation", "opinion"]),
        ("在线平台", ["social media", "online platform", "platform"]),
        ("数字痕迹", ["digital trace", "digital footprint"]),
        ("因果推断", ["causal inference", "natural experiment"]),
        ("实验", ["experiment"]),
        ("仿真与ABM", ["agent-based", "agent based", "abm", "social simulation"]),
        ("LLM智能体", ["large language model", "llm", "generative ai"]),
        ("文本计算", ["text as data", "text mining", "natural language"]),
        ("城市与流动", ["mobility", "migration", "urban", "segregation"]),
        ("方法论", ["method", "measurement", "estimation"]),
    ]
    text = f"{paper.title} {paper.abstract}"
    tags = [tag for tag, keywords in mapping if keyword_hits(text, keywords)]
    return tags[:3] or ["方法论"]


def apply_fallback(paper: Paper) -> None:
    paper.tldr = _first_sentence(paper.abstract)
    paper.tags = _fallback_tags(paper)
    paper.score = paper.rule_score


def _build_messages(batch: list[Paper], cfg: dict) -> list[dict]:
    lcfg = cfg["llm"]
    tag_list = "、".join(lcfg["tags"])
    items = [
        {
            "id": paper.id,
            "title": paper.title,
            "venue": paper.venue,
            "abstract": paper.abstract[: int(lcfg["max_abstract_chars"])],
        }
        for paper in batch
    ]
    user_prompt = (
        "请评估以下论文对“计算社会科学 / 复杂网络 / 社会网络分析”读者的价值。\n"
        f"可用标签：{tag_list}\n\n"
        "评分标准：\n"
        "- 9-10：该领域核心问题、方法或重要发现，必读\n"
        "- 7-8：明确相关，有方法或实证价值\n"
        "- 5-6：边缘相关\n"
        "- 0-4：基本不相关（纯物理/材料/生物、纯工程、与网络和社会行为无关）\n\n"
        "对每篇输出：score（0-10，可一位小数）、tldr_zh（一句中文导读，不超过60字，"
        "说清楚做了什么和发现了什么，不要空话）、tags（1-3个，只能从可用标签中选）、"
        "reason（一句中文，说明相关性，供调试）。\n\n"
        f"论文列表（JSON）：\n{json.dumps(items, ensure_ascii=False)}\n\n"
        '只输出 JSON，格式为：{"results":[{"id":"...","score":7.5,'
        '"tldr_zh":"...","tags":["..."],"reason":"..."}]}'
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def _chat(api_key: str, cfg: dict, messages: list[dict]) -> dict:
    lcfg = cfg["llm"]
    body = {
        "model": lcfg["model"],
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"},
    }
    url = f"{lcfg['base_url'].rstrip('/')}/chat/completions"
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=120,
            )
            if response.status_code in {429, 500, 502, 503, 504}:
                raise requests.HTTPError(f"HTTP {response.status_code}")
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"DeepSeek request failed: {last_error}")


def _parse_response(payload: dict) -> tuple[list[dict], dict]:
    content = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    data = json.loads(content)
    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError("LLM response missing results array")
    return results, (payload.get("usage") or {})


def enrich_with_llm(papers: list[Paper], cfg: dict, api_key: str) -> dict:
    lcfg = cfg["llm"]
    batch_size = int(lcfg["batch_size"])
    by_id = {paper.id: paper for paper in papers}
    stats = {"batches": 0, "failures": 0, "prompt_tokens": 0, "completion_tokens": 0}

    for start in range(0, len(papers), batch_size):
        batch = papers[start : start + batch_size]
        stats["batches"] += 1
        try:
            payload = _chat(api_key, cfg, _build_messages(batch, cfg))
            results, usage = _parse_response(payload)
            stats["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
            stats["completion_tokens"] += int(usage.get("completion_tokens") or 0)
            returned: set[str] = set()
            for item in results:
                paper = by_id.get(str(item.get("id")))
                if not paper:
                    continue
                returned.add(paper.id)
                score = float(item.get("score") or 0)
                paper.score = round(min(10.0, max(0.0, score) + 0.05 * paper.rule_score), 3)
                paper.tldr_zh = str(item.get("tldr_zh") or "").strip()[:120]
                tags = [str(tag).strip() for tag in (item.get("tags") or []) if str(tag).strip()]
                paper.tags = [tag for tag in tags if tag in lcfg["tags"]][:3]
                paper.reason = str(item.get("reason") or "").strip()
            for paper in batch:
                if paper.id not in returned:
                    apply_fallback(paper)
        except Exception as exc:  # noqa: BLE001
            stats["failures"] += 1
            print(f"[llm] batch {start // batch_size + 1} failed: {exc}", flush=True)
            for paper in batch:
                apply_fallback(paper)
    return stats
