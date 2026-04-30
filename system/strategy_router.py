from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = BASE_DIR / "config" / "deck_intent_taxonomy.json"
REGISTRY_PATH = BASE_DIR / "config" / "variant_strategy_registry.json"

PRIVATE_PATTERNS = [
    re.compile(r"[A-Za-z]:\\(?:[^\\/:*?\"<>|\r\n]+\\)*[^\\/:*?\"<>|\r\n]*"),
    re.compile(r"/(?:Users|home)/[^\s\"']+"),
    re.compile(r"\b(?:drive[_-]?id|token|secret|api[_-]?key)\b\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
]

URL_RE = re.compile(r"https?://[^\s)>\"]+", re.IGNORECASE)
PATH_RE = re.compile(r"(?:[A-Za-z]:\\[^\s\"<>|]+|(?:\.{1,2}[\\/])?[^\s\"<>|]+\.(?:pdf|pptx|docx|xlsx|csv|txt|md|json))", re.IGNORECASE)
SLIDE_COUNT_PATTERNS = [
    re.compile(r"\b(?P<count>\d{1,2})\s*[- ]?\s*(?:slide|slides|page|pages)\b", re.IGNORECASE),
    re.compile(r"\b(?P<count>\d{1,2})\s*[- ]?\s*(?:slide|slides|page|pages)?\s*(?:deck|presentation)\b", re.IGNORECASE),
    re.compile(r"(?P<count>\d{1,2})\s*(?:장|쪽|페이지|슬라이드)\b", re.IGNORECASE),
]
KOREAN_COUNT_WORDS = {
    "한": 1,
    "하나": 1,
    "두": 2,
    "둘": 2,
    "세": 3,
    "셋": 3,
    "네": 4,
    "넷": 4,
    "다섯": 5,
    "여섯": 6,
    "일곱": 7,
    "여덟": 8,
    "아홉": 9,
    "열": 10,
}
KOREAN_COUNT_PATTERN = re.compile(r"(?P<count>한|하나|두|둘|세|셋|네|넷|다섯|여섯|일곱|여덟|아홉|열)\s*(?:장|쪽|페이지|슬라이드)")


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(public_safe(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def public_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): public_safe(item) for key, item in value.items() if not any(p.search(str(key)) for p in PRIVATE_PATTERNS)}
    if isinstance(value, list):
        return [public_safe(item) for item in value]
    if isinstance(value, str):
        text = value
        for pattern in PRIVATE_PATTERNS:
            text = pattern.sub("[redacted]", text)
        return text
    return value


def bounded(text: str, limit: int = 480) -> str:
    cleaned = re.sub(r"\s+", " ", public_safe(text)).strip()
    return cleaned[:limit] + ("..." if len(cleaned) > limit else "")


def title_case(text: str) -> str:
    small = {"a", "an", "and", "as", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with"}
    words = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?|[가-힣]+", text)
    titled = []
    for index, word in enumerate(words):
        lowered = word.lower()
        if index > 0 and lowered in small:
            titled.append(lowered)
        elif word.isupper() and len(word) <= 4:
            titled.append(word)
        else:
            titled.append(word[:1].upper() + word[1:].lower())
    return " ".join(titled)


def extract_requested_slide_count(text: str) -> dict[str, Any] | None:
    for pattern in SLIDE_COUNT_PATTERNS:
        match = pattern.search(text)
        if match:
            count = int(match.group("count"))
            if 1 <= count <= 40:
                return {"value": count, "evidence": match.group(0)}
    match = KOREAN_COUNT_PATTERN.search(text)
    if match:
        count = KOREAN_COUNT_WORDS.get(match.group("count"))
        if count:
            return {"value": count, "evidence": match.group(0)}
    return None


def strip_command_wrappers(text: str) -> str:
    cleaned = re.sub(r"\b(?:please\s+)?create\s+(?:an?\s+)?(?:\d{1,2}\s*[- ]?\s*)?(?:auto[- ]mode\s+)?", " ", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:make|generate|build)\s+(?:an?\s+)?(?:\d{1,2}\s*[- ]?\s*)?(?:auto[- ]mode\s+)?", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bproduce\s+two\s+visually\s+distinct\s+variants\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:presentation|deck|proposal|training deck|slides?)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = strip_korean_slide_meta(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;-")
    return cleaned


def extract_korean_topic_list(text: str) -> list[str]:
    topics: list[str] = []
    for match in re.finditer(r"(?:다음|아래|목록|항목)[^:：\n]{0,80}[:：]\s*([^。.\n]+)", text):
        raw = match.group(1)
        for item in re.split(r"\s*(?:,|，|、|ㆍ|·|/| 및 | 그리고 )\s*", raw):
            cleaned = re.sub(r"\s+", " ", item).strip(" \t\r\n-•,.;:：")
            cleaned = re.sub(r"^(?:각\s*)?슬라이드(?:에|마다)?\s*", "", cleaned)
            if cleaned and len(cleaned) <= 32 and re.search(r"[가-힣A-Za-z0-9]", cleaned):
                topics.append(cleaned)
    unique: list[str] = []
    for topic in topics:
        if topic not in unique:
            unique.append(topic)
    return unique[:20]


def strip_korean_slide_meta(value: str) -> str:
    text = re.sub(r"\s+", " ", value).strip(" \t\r\n-•,.;:：")
    text = re.sub(r"^\d{1,2}\s*번\s*슬라이드(?:는|은)?\s*", "", text)
    text = re.sub(r"^\d{1,2}\s*번\s*부터\s*\d{1,2}\s*번\s*까지(?:는|은)?\s*", "", text)
    text = re.sub(r"^(?:각\s*)?슬라이드(?:에|마다)?\s*", "", text)
    text = re.sub(
        r"\s*(?:으로|로)?\s*슬라이드\s*총?\s*\d{1,2}\s*(?:장|쪽|페이지|슬라이드)?\s*(?:구성|작성|제작)?\s*$",
        "",
        text,
    )
    text = re.sub(r"\s+(?:으로|로)$", "", text)
    return text.strip(" \t\r\n-•,.;:：")


def phrase_after(label_pattern: str, text: str) -> str | None:
    match = re.search(label_pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    value = match.group(1).strip()
    value = re.split(r"\.\s+(?:Audience|Focus|Produce)\b|\.$", value, maxsplit=1, flags=re.IGNORECASE)[0]
    return re.sub(r"\s+", " ", value).strip(" .,:;-") or None


def split_focus_areas(value: str | None) -> list[str]:
    if not value:
        return []
    value = re.sub(r"\band\b", ",", value, flags=re.IGNORECASE)
    value = value.replace(" 및 ", ",").replace(" 그리고 ", ",")
    areas = []
    for item in value.split(","):
        cleaned = re.sub(r"\s+", " ", item).strip(" .,:;-")
        if cleaned:
            areas.append(cleaned)
    return areas[:10]


def derive_deck_title(prompt: str, *, project_name: str | None = None) -> str:
    if project_name:
        return title_case(strip_command_wrappers(project_name))[:80] or "Untitled Deck"
    lowered = prompt.lower()
    if re.search(r"[가-힣]", prompt):
        first_sentence = re.split(r"[。.!?\n]", prompt.strip(), maxsplit=1)[0]
        korean_title = strip_korean_slide_meta(first_sentence)
        if korean_title:
            return bounded(korean_title, 80)
    about = phrase_after(r"\babout\s+(.+?)(?=\.\s+(?:Audience|Focus|Produce)\b|$)", prompt)
    if about:
        about = re.sub(r"^(?:improving|introducing|building|creating|planning|for)\s+", "", about, flags=re.IGNORECASE)
        about = re.sub(r"\bduring\b.+$", "", about, flags=re.IGNORECASE).strip()
        title = title_case(about)
        if "exhibition" in lowered and "installation" in title.lower():
            title = re.sub(r"\bInstallations?\b", "Exhibition", title)
        if any(token in lowered for token in ["sponsor", "sponsorship"]) and "sponsor" not in title.lower():
            title = f"{title} Sponsorship"
        return title[:80] or "Untitled Deck"
    introducing = phrase_after(r"\bintroducing\s+(.+?)(?=\.\s+(?:Audience|Focus|Produce)\b|$)", prompt)
    if introducing:
        return title_case(introducing)[:80] or "Untitled Deck"
    for_match = phrase_after(r"\bfor\s+(.+?)(?=\.\s+(?:Audience|Focus|Produce)\b|$)", prompt)
    if for_match:
        introduction_tail = re.search(r"\bintroducing\s+(.+)$", for_match, flags=re.IGNORECASE)
        if introduction_tail:
            return title_case(introduction_tail.group(1))[:80] or "Untitled Deck"
        for_match = re.sub(r"^(?:a|an|the)\s+", "", for_match, flags=re.IGNORECASE)
        return title_case(strip_command_wrappers(for_match))[:80] or "Untitled Deck"
    return title_case(strip_command_wrappers(prompt.split(".")[0] if prompt.strip() else "Untitled Deck"))[:80] or "Untitled Deck"


def derive_objective(prompt: str, title: str) -> str:
    lowered = prompt.lower()
    if "sponsorship proposal" in lowered:
        return "Win sponsor support with a clear visitor, visibility, and impact story."
    if "training deck" in lowered or "safety practices" in lowered:
        return "Teach supervisors the daily behaviors that keep human-robot work safe."
    if "triage" in lowered and "flow" in lowered:
        return "Improve triage flow with clearer operating decisions."
    about = phrase_after(r"\babout\s+(.+?)(?=\.\s+(?:Audience|Focus|Produce)\b|$)", prompt)
    if about:
        return title_case(about)
    return f"Clarify the plan for {title}."


def transformed_request_from_prompt(prompt: str, *, project_name: str | None = None) -> dict[str, Any]:
    title = derive_deck_title(prompt, project_name=project_name)
    audience = phrase_after(r"\bAudience:\s*(.+?)(?=\.\s+(?:Focus|Produce)\b|$)", prompt)
    explicit_list_items = extract_korean_topic_list(prompt)
    focus = split_focus_areas(phrase_after(r"\bFocus\s+on\s+(.+?)(?=\.\s+Produce\b|$)", prompt)) or explicit_list_items
    slide_count = extract_requested_slide_count(prompt)
    return {
        "deck_title": bounded(title, 100),
        "audience": bounded(audience or "general audience", 160),
        "objective": bounded(derive_objective(prompt, title), 180),
        "focus_areas": [bounded(item, 80) for item in focus],
        "explicit_list_items": [bounded(item, 80) for item in explicit_list_items],
        "requested_slide_count": slide_count,
        "raw_command_removed": True,
    }


def detect_language(text: str) -> str:
    return "ko-KR" if re.search(r"[가-힣]", text) else "en-US"


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    hits: list[str] = []
    for keyword in keywords:
        lowered_keyword = keyword.lower()
        if not lowered_keyword:
            continue
        if re.fullmatch(r"[a-z0-9]{1,3}", lowered_keyword):
            pattern = rf"(?<![a-z0-9]){re.escape(lowered_keyword)}(?![a-z0-9])"
            if re.search(pattern, lowered):
                hits.append(keyword)
            continue
        if re.search(r"[a-z0-9]", lowered_keyword):
            pattern = rf"(?<![a-z0-9]){re.escape(lowered_keyword)}(?![a-z0-9])"
            if re.search(pattern, lowered):
                hits.append(keyword)
            continue
        if lowered_keyword in lowered:
            hits.append(keyword)
    return hits


def is_food_product_launch_request(text: str) -> bool:
    product_hits = keyword_hits(text, ["food", "beverage", "식품", "음료", "푸드", "제품", "상품", "신상품", "packshot", "ingredient", "유통"])
    launch_hits = keyword_hits(text, ["launch", "런칭", "출시", "홍보", "campaign", "캠페인", "promotion", "프로모션", "retail"])
    return bool(product_hits and launch_hits)


def is_public_environment_civic_request(text: str) -> bool:
    domain_hits = keyword_hits(
        text,
        [
            "wetland",
            "wetlands",
            "tidal",
            "coastal",
            "habitat",
            "flood",
            "flood-risk",
            "storm",
            "restoration",
            "restore",
            "resilience",
            "permit",
            "environment",
            "environmental",
            "community",
        ],
    )
    civic_hits = keyword_hits(
        text,
        [
            "authority",
            "agency",
            "public",
            "regional",
            "municipal",
            "city",
            "community advisory board",
            "advisory board",
        ],
    )
    return len(domain_hits) >= 2 and bool(civic_hits)


def has_strong_finance_context(text: str) -> bool:
    finance_domain_hits = keyword_hits(
        text,
        [
            "financial performance",
            "quarterly financial",
            "financial review",
            "revenue",
            "margin",
            "profit",
            "loss",
            "cash flow",
            "budget variance",
            "kpi",
            "매출",
            "실적",
            "손익",
        ],
    )
    finance_role_only_hits = keyword_hits(text, ["finance lead", "finance director", "cfo"])
    return bool(finance_domain_hits) or len(finance_role_only_hits) >= 2


def detect_action(text: str, taxonomy: dict[str, Any]) -> tuple[str, list[str]]:
    objective_keywords = taxonomy.get("objective_keywords", {})
    scores: list[tuple[int, str, list[str]]] = []
    for objective, keywords in objective_keywords.items():
        hits = keyword_hits(text, keywords)
        if hits:
            scores.append((len(hits), objective, hits))
    if not scores:
        return "create", []
    scores.sort(reverse=True)
    return scores[0][1], scores[0][2]


def detect_mode_evidence(text: str, requested_mode: str) -> dict[str, Any]:
    auto_terms = ["auto mode", "automatic", "without approval", "알아서", "전부 자동", "처음부터 자동", "승인 없이", "자동으로"]
    assistant_terms = ["review", "approve", "검토", "승인", "먼저 계획"]
    auto_hits = keyword_hits(text, auto_terms)
    assistant_hits = keyword_hits(text, assistant_terms)
    return {
        "requested_mode": requested_mode,
        "auto_evidence": auto_hits,
        "assistant_evidence": assistant_hits,
        "ambiguous": bool(auto_hits and assistant_hits),
        "reason": "explicit_mode_argument" if requested_mode in {"assistant", "auto"} else "default_assistant",
    }


def source_kind_from_value(value: str) -> str:
    lower = value.lower()
    if URL_RE.match(value):
        return "url"
    if lower.endswith((".pptx", ".ppt")):
        return "existing_deck"
    if lower.endswith((".docx", ".pdf", ".md", ".txt")):
        return "document"
    if lower.endswith((".xlsx", ".csv")):
        return "spreadsheet"
    if lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return "image"
    return "unknown"


def public_source_label(value: str) -> str:
    if URL_RE.match(value):
        return re.sub(r"([?&](?:token|key|sig|signature)=)[^&]+", r"\1[redacted]", value, flags=re.IGNORECASE)
    name = Path(value).name if value else "source"
    return f"[local-source:{bounded(name, 96)}]"


def extract_entities(text: str) -> dict[str, list[str]]:
    entities = {
        "company": [],
        "product": [],
        "place": [],
        "person": [],
        "sector": [],
        "event": [],
        "metric": [],
    }
    metric_hits = re.findall(r"\b\d+(?:\.\d+)?\s?(?:%|억원|원|달러|usd|users|명|건|x)\b", text, flags=re.IGNORECASE)
    entities["metric"] = metric_hits[:8]
    sector_map = {
        "saas": "SaaS",
        "공공": "public sector",
        "여행": "travel",
        "food": "food",
        "식품": "food",
        "fashion": "fashion",
        "패션": "fashion",
        "자동차": "automotive",
        "automotive": "automotive",
        "k-pop": "K-POP",
        "kpop": "K-POP",
    }
    lowered = text.lower()
    entities["sector"] = sorted({label for key, label in sector_map.items() if key in lowered})
    capitalized = re.findall(r"\b[A-Z][A-Za-z0-9&.-]{2,}(?:\s+[A-Z][A-Za-z0-9&.-]{2,}){0,2}\b", text)
    entities["company"] = capitalized[:5]
    quoted = re.findall(r"[\"'“”‘’]([^\"'“”‘’]{2,48})[\"'“”‘’]", text)
    entities["product"] = quoted[:5]
    return entities


def structure_signals(text: str) -> list[str]:
    signals = []
    checks = [
        ("numbered_report", r"(?:^|\s)(?:1\.|①|첫째|second|third)"),
        ("narrative_article", r"(story|article|narrative|기사|스토리)"),
        ("product_listing", r"(feature|spec|catalog|제품|스펙|카탈로그)"),
        ("financial_data", r"(revenue|margin|kpi|매출|손익|실적|kpi)"),
        ("syllabus", r"(module|lesson|curriculum|강의|교육|커리큘럼)"),
        ("portfolio", r"(portfolio|works|case study|포트폴리오|작품|사례)"),
        ("policy_memo", r"(policy|procurement|grant|정책|조달|보조금|입찰)"),
        ("campaign_brief", r"(campaign|launch|promotion|캠페인|런칭|홍보)"),
    ]
    for name, pattern in checks:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            signals.append(name)
    return signals


def create_request_intake(
    prompt: str,
    *,
    mode: str = "assistant",
    explicit_sources: list[str] | None = None,
    search_topics: list[str] | None = None,
    project_name: str | None = None,
) -> dict[str, Any]:
    taxonomy = load_json(TAXONOMY_PATH)
    explicit_sources = explicit_sources or []
    search_topics = search_topics or []
    transformed_request = transformed_request_from_prompt(prompt, project_name=project_name)
    requested_slide_count = transformed_request.get("requested_slide_count")
    detected_refs = URL_RE.findall(prompt) + PATH_RE.findall(prompt)
    source_materials = []
    for index, value in enumerate([*explicit_sources, *detected_refs], start=1):
        source_materials.append(
            {
                "source_id": f"src-{index:02d}",
                "kind": source_kind_from_value(value),
                "public_label": public_source_label(value),
                "supplied_via": "argument" if value in explicit_sources else "prompt",
                "readable_candidate": source_kind_from_value(value) not in {"url", "unknown"},
            }
        )
    for offset, topic in enumerate(search_topics, start=len(source_materials) + 1):
        source_materials.append(
            {
                "source_id": f"src-{offset:02d}",
                "kind": "search_topic",
                "public_label": bounded(topic, 120),
                "supplied_via": "argument",
                "search_intent": True,
            }
        )
    if len(prompt) > 700 and not source_materials:
        source_materials.append(
            {
                "source_id": "src-01",
                "kind": "notes",
                "public_label": "pasted-material",
                "supplied_via": "prompt",
                "readable_candidate": True,
            }
        )
    action, action_evidence = detect_action(prompt, taxonomy)
    return {
        "contract": "ppt-maker.request-intake.v1",
        "created_at": utc_now(),
        "original_request_excerpt": bounded(prompt, 600),
        "detected_language": detect_language(prompt),
        "locale": detect_language(prompt),
        "project_name_candidate": transformed_request["deck_title"],
        "transformed_request": transformed_request,
        "requested_slide_count": requested_slide_count,
        "requested_action": action,
        "action_evidence": action_evidence,
        "source_materials": source_materials,
        "explicit_constraints": [
            *keyword_hits(prompt, ["public", "공공", "investor", "투자", "auto", "자동", "review", "검토", "10 slides", "15장"]),
            *([f"requested_slide_count={requested_slide_count['value']}"] if requested_slide_count else []),
        ],
        "missing_constraints": [
            item
            for item in ["exact slide count", "brand/template preference", "source rights confirmation"]
            if item != "exact slide count" or not requested_slide_count
        ],
        "assumptions": [
            "Use public-safe summaries rather than raw source payloads.",
            "If source content is unreadable, proceed with clearly labeled assumptions.",
        ],
        "mode_evidence": detect_mode_evidence(prompt, mode),
    }


def summarize_sources(
    prompt: str,
    request_intake: dict[str, Any],
    *,
    explicit_sources: list[str] | None = None,
) -> dict[str, Any]:
    explicit_sources = explicit_sources or []
    source_payloads: list[dict[str, Any]] = []
    actual_by_label = {public_source_label(value): value for value in explicit_sources}
    if not request_intake.get("source_materials"):
        return {
            "contract": "ppt-maker.source-summary.v1",
            "created_at": utc_now(),
            "sources": [],
            "overall_confidence": 0.35,
            "assumptions": ["No readable external source was supplied; classify from request text only."],
            "unresolved_blockers": [],
        }
    for source in request_intake["source_materials"]:
        public_label = source["public_label"]
        kind = source["kind"]
        text = ""
        blockers = []
        if public_label in actual_by_label:
            path = Path(actual_by_label[public_label])
            try:
                if path.exists() and path.is_file() and path.suffix.lower() in {".txt", ".md", ".json", ".csv"}:
                    text = path.read_text(encoding="utf-8", errors="replace")[:20000]
                elif path.exists() and path.is_file():
                    blockers.append("Source exists but binary or complex parsing is not enabled for sparse intake.")
                else:
                    blockers.append("Source is not readable from the selected workspace context.")
            except Exception as exc:
                blockers.append(f"Source read failed: {exc.__class__.__name__}")
        elif kind == "notes":
            text = prompt[:20000]
        elif kind == "search_topic":
            text = str(public_label)
        elif kind == "url":
            blockers.append("URL fetching is not performed by default in local sparse intake.")
        else:
            blockers.append("Source reference was detected but not read; using request text only.")
        evidence_text = text or prompt
        source_payloads.append(
            {
                "source_id": source["source_id"],
                "kind": kind,
                "public_label": public_label,
                "title_candidates": [bounded((text or public_label).splitlines()[0] if (text or public_label) else public_label, 96)],
                "extracted_entities": extract_entities(evidence_text),
                "content_structure_signals": structure_signals(evidence_text),
                "evidence_snippets": [bounded(evidence_text, 220)] if evidence_text else [],
                "confidence": 0.76 if text and not blockers else 0.45,
                "unresolved_extraction_blockers": blockers,
            }
        )
    blockers = [
        {"source_id": item["source_id"], "blocker": blocker}
        for item in source_payloads
        for blocker in item.get("unresolved_extraction_blockers", [])
    ]
    return {
        "contract": "ppt-maker.source-summary.v1",
        "created_at": utc_now(),
        "sources": source_payloads,
        "overall_confidence": round(sum(item["confidence"] for item in source_payloads) / max(1, len(source_payloads)), 2),
        "assumptions": ["Unreadable sources are treated as context signals, not factual evidence."] if blockers else [],
        "unresolved_blockers": blockers,
    }


def classify_intent(request_intake: dict[str, Any], source_summary: dict[str, Any]) -> dict[str, Any]:
    taxonomy = load_json(TAXONOMY_PATH)
    text_parts = [request_intake.get("original_request_excerpt", "")]
    for source in source_summary.get("sources", []):
        text_parts.extend(source.get("evidence_snippets", []))
        text_parts.extend(source.get("content_structure_signals", []))
        for values in source.get("extracted_entities", {}).values():
            text_parts.extend(values)
    text = " ".join(str(part) for part in text_parts)
    family_scores: list[tuple[int, str, dict[str, Any], list[str]]] = []
    for family in taxonomy["families"]:
        hits = keyword_hits(text, family.get("keywords", []))
        subtype_hits_for_family = []
        for subtype in family.get("subtypes", []):
            subtype_hits_for_family.extend(keyword_hits(text, subtype.get("keywords", [])))
        all_hits = [*hits, *subtype_hits_for_family]
        if all_hits:
            family_scores.append((len(all_hits), family["id"], family, all_hits))
    tie_priority = {
        "media_entertainment": 30,
        "event_travel": 28,
        "marketing_campaign": 26,
        "product_introduction": 20,
        "public_institution_report": 18,
        "sales_proposal": 16,
        "ir_pitch": 14,
        "executive_report": 12,
        "research_analysis": 10,
        "education_training": 8,
        "portfolio": 6,
        "status_update": 4,
    }
    if family_scores:
        family_scores.sort(key=lambda item: (item[0], len(item[3]), tie_priority.get(item[1], 0)), reverse=True)
        _, family_id, family, family_hits = family_scores[0]
    else:
        family_id, family, family_hits = "unknown", {}, []
    subtype_id = "general"
    subtype_hits: list[str] = []
    if family:
        subtype_scores = []
        for subtype in family.get("subtypes", []):
            hits = keyword_hits(text, subtype.get("keywords", []))
            if hits:
                subtype_scores.append((len(hits), subtype["id"], hits))
        if subtype_scores:
            subtype_scores.sort(reverse=True)
            _, subtype_id, subtype_hits = subtype_scores[0]
        elif family.get("subtypes"):
            subtype_id = family["subtypes"][0]["id"]
    if is_food_product_launch_request(text):
        product_family = next((item for item in taxonomy["families"] if item["id"] == "product_introduction"), None)
        if product_family:
            family_id = "product_introduction"
            family = product_family
            subtype_id = "food_beverage"
            family_hits = sorted(set([*family_hits, *keyword_hits(text, product_family.get("keywords", [])), "food_product_launch_tiebreak"]))
            subtype_hits = sorted(set([*subtype_hits, "food_beverage"]))
    if is_public_environment_civic_request(text) and not has_strong_finance_context(text):
        public_family = next((item for item in taxonomy["families"] if item["id"] == "public_institution_report"), None)
        if public_family:
            family_id = "public_institution_report"
            family = public_family
            subtype_id = "environment_safety"
            family_hits = sorted(
                set(
                    [
                        *family_hits,
                        *keyword_hits(text, public_family.get("keywords", [])),
                        "public_environment_civic_tiebreak",
                    ]
                )
            )
            subtype_hits = sorted(set([*subtype_hits, "environment_safety"]))
    evidence_count = len(family_hits) + len(subtype_hits)
    confidence = min(0.95, 0.25 + evidence_count * 0.12 + (0.1 if source_summary.get("sources") else 0.0))
    if family_id == "unknown":
        confidence = 0.25
    elif family_id == "public_institution_report" and family_hits:
        confidence = max(confidence, 0.61)
    elif subtype_id != "general" and evidence_count >= 2:
        confidence = max(confidence, 0.61)
    audience = family.get("default_audience", "general audience")
    for label, keywords in taxonomy.get("audience_keywords", {}).items():
        if keyword_hits(text, keywords):
            audience = label
            break
    objective = request_intake.get("requested_action") or family.get("default_objective", "create")
    needs_clarification = []
    if confidence < taxonomy["classification_policy"]["low_confidence_threshold"]:
        needs_clarification.append("Deck family or audience is uncertain enough that Assistant mode may ask one concise question.")
    transformed_request = request_intake.get("transformed_request") or {}
    return {
        "contract": "ppt-maker.intent-profile.v1",
        "created_at": utc_now(),
        "topic": bounded(transformed_request.get("deck_title") or request_intake.get("project_name_candidate") or "Untitled Deck", 120),
        "deck_family": family_id,
        "sector_subtype": subtype_id,
        "audience": bounded(transformed_request.get("audience") or audience, 160),
        "objective": bounded(transformed_request.get("objective") or objective, 180),
        "decision_context": "decision_required" if family_id in {"executive_report", "ir_pitch", "sales_proposal"} else "inform_or_explain",
        "tone": family.get("default_tone", ["clear", "credible"]),
        "content_density": family.get("default_density", "medium"),
        "visual_style_bias": "visual-first" if family_id in {"portfolio", "product_introduction", "event_travel", "media_entertainment"} else "evidence-first",
        "evidence_strength": "source-backed" if source_summary.get("sources") and not source_summary.get("unresolved_blockers") else "request-inferred",
        "confidence": round(confidence, 2),
        "classification_evidence": {
            "family_keyword_hits": family_hits,
            "subtype_keyword_hits": subtype_hits,
            "candidate_families": [{"family": item[1], "score": item[0], "hits": item[3]} for item in family_scores[:4]],
            "method": "deterministic_keyword_entity_matching"
        },
        "assumptions": [
            "Intent is inferred from bounded request/source summaries and may be refined by the user.",
            *source_summary.get("assumptions", []),
        ],
        "needs_clarification": needs_clarification,
    }


def strategy_by_id(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["strategy_id"]: item for item in registry["strategies"]}


def resolve_strategy_id(strategy_id: str, registry: dict[str, Any]) -> str:
    return registry.get("aliases", {}).get(strategy_id, strategy_id)


def route_strategies(
    request_intake: dict[str, Any],
    source_summary: dict[str, Any],
    intent_profile: dict[str, Any],
    *,
    mode: str = "assistant",
    explicit_strategy: str | None = None,
) -> dict[str, Any]:
    registry = load_json(REGISTRY_PATH)
    strategies = strategy_by_id(registry)
    fallback = registry["fallbacks"]["general_unknown_intent"]
    threshold = load_json(TAXONOMY_PATH)["classification_policy"]["low_confidence_threshold"]
    selected_mapping = None
    rejected = []
    family = intent_profile.get("deck_family")
    subtype = intent_profile.get("sector_subtype")
    request_text = " ".join(
        [
            str(request_intake.get("original_request_excerpt", "")),
            str(request_intake.get("requested_action", "")),
            " ".join(str(item) for item in request_intake.get("action_evidence", [])),
        ]
    ).lower()

    def mapping_matches_context(mapping: dict[str, Any]) -> tuple[bool, str | None]:
        requires = mapping.get("requires_keywords", [])
        avoids = mapping.get("avoid_keywords", [])
        if requires and not keyword_hits(request_text, requires):
            return False, f"missing required context keywords {requires}"
        avoid_hits = keyword_hits(request_text, avoids)
        if avoid_hits:
            return False, f"blocked by context keywords {avoid_hits}"
        return True, None

    if explicit_strategy:
        canonical = resolve_strategy_id(explicit_strategy, registry)
        if canonical in strategies:
            selected_mapping = {
                "mapping_id": "explicit_user_strategy",
                "variant_a": canonical,
                "variant_b": strategies[canonical].get("fallback_strategy_id") or fallback["variant_b"],
                "why": "Explicit user strategy preference was honored within the approved registry."
            }
    if not selected_mapping and intent_profile.get("confidence", 0) >= threshold:
        for mapping in registry["recommended_ab_mappings"]:
            if mapping["family"] == family and (not mapping.get("subtypes") or subtype in mapping.get("subtypes", [])):
                context_ok, context_reason = mapping_matches_context(mapping)
                if context_ok:
                    selected_mapping = mapping
                    break
                rejected.append({"mapping_id": mapping["mapping_id"], "reason": context_reason or "context did not match"})
                continue
            if mapping["family"] == family:
                rejected.append({"mapping_id": mapping["mapping_id"], "reason": f"subtype {subtype} did not match"})
    fallback_used = selected_mapping is None
    if fallback_used:
        selected_mapping = {
            "mapping_id": "general_unknown_intent",
            "variant_a": fallback["variant_a"],
            "variant_b": fallback["variant_b"],
            "why": fallback["trigger"],
        }
    variant_a = resolve_strategy_id(selected_mapping["variant_a"], registry)
    variant_b = resolve_strategy_id(selected_mapping["variant_b"], registry)
    if variant_a == variant_b:
        variant_b = strategies[variant_a].get("fallback_strategy_id") or fallback["variant_b"]
    assumptions = []
    unresolved = []
    if source_summary.get("unresolved_blockers"):
        assumptions.append("Some sources were unreadable; routing uses request/source labels plus any bounded summaries.")
    if fallback_used:
        assumptions.append("Fallback pair is decision-first plus story-first for safe unknown-intent coverage.")
    if mode == "assistant" and intent_profile.get("confidence", 0) < threshold:
        unresolved.append("One clarification may be useful if deck family, audience, or source rights materially changes the plan.")
    return {
        "contract": "ppt-maker.routing-report.v1",
        "created_at": utc_now(),
        "mode": mode,
        "fallback_used": fallback_used,
        "fallback_reason": selected_mapping["why"] if fallback_used else None,
        "selected": {
            "variant_a": {"strategy_id": variant_a, "profile": strategies[variant_a]},
            "variant_b": {"strategy_id": variant_b, "profile": strategies[variant_b]},
            "mapping_id": selected_mapping["mapping_id"],
            "why_both_are_useful": selected_mapping.get("why", ""),
        },
        "rejected_candidates": rejected[:6],
        "confidence": round(min(intent_profile.get("confidence", 0.0) + (0.08 if not fallback_used else 0.0), 0.98), 2),
        "routing_evidence": {
            "family": family,
            "subtype": subtype,
            "audience": intent_profile.get("audience"),
            "objective": intent_profile.get("objective"),
            "classification_evidence": intent_profile.get("classification_evidence", {}),
        },
        "assumptions": assumptions,
        "unresolved_ambiguity": unresolved,
        "policy": {
            "auto_low_confidence_continues_with_fallback": True,
            "assistant_may_ask_one_material_question": True,
            "strategy_candidates_are_registry_bounded": True,
        },
    }


def run_sparse_request_pipeline(
    prompt: str,
    project_dir: Path,
    *,
    mode: str = "assistant",
    explicit_sources: list[str] | None = None,
    search_topics: list[str] | None = None,
    project_name: str | None = None,
    explicit_strategy: str | None = None,
) -> dict[str, Any]:
    intake = create_request_intake(
        prompt,
        mode=mode,
        explicit_sources=explicit_sources,
        search_topics=search_topics,
        project_name=project_name,
    )
    source_summary = summarize_sources(prompt, intake, explicit_sources=explicit_sources)
    intent = classify_intent(intake, source_summary)
    routing = route_strategies(intake, source_summary, intent, mode=mode, explicit_strategy=explicit_strategy)
    json_dump(project_dir / "request-intake.json", intake)
    json_dump(project_dir / "source-summary.json", source_summary)
    json_dump(project_dir / "intent-profile.json", intent)
    json_dump(project_dir / "routing-report.json", routing)
    return {
        "request_intake": intake,
        "source_summary": source_summary,
        "intent_profile": intent,
        "routing_report": routing,
    }
