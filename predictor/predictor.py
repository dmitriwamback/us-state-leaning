import json
import re
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
from typing import Optional

from perplexity import Perplexity
from compute_lean import compute_lean_from_sources


MODEL = "sonar-pro"
RECENCY_DAYS = 45

MODE_SENATE_PRESIDENTIAL = "senate_presidential_polling"
MODE_GOVERNOR = "governor_polling"

_RACE_TARGETS = {
    MODE_SENATE_PRESIDENTIAL: {"senate", "presidential"},
    MODE_GOVERNOR: {"governor"},
}

_RACE_DESCRIPTIONS = {
    MODE_SENATE_PRESIDENTIAL: "the Senate and/or Presidential race",
    MODE_GOVERNOR: "the Governor's race",
}


def _build_system_prompt(mode: str) -> str:
    race_description = _RACE_DESCRIPTIONS[mode]
    all_race_types = sorted(_RACE_TARGETS[mode] | {"other_context"})
    valid_race_types_commas = ", ".join(f'"{r}"' for r in all_race_types)
    valid_race_types_pipes = " | ".join(f'"{r}"' for r in all_race_types)

    return f"""You are a political analyst. Based on current polling and news from the last {RECENCY_DAYS} days, determine the current margin for {race_description} in the state you're asked about.

For each source you find, report its name, a direct link, its race_type (must be one of: {valid_race_types_commas} -- use "other_context" for anything that isn't actually {race_description}, like a different race or a structural index), the party it favors (D, R, or EVEN), and the margin as a number when available, a short detail of what it found, and the date range the data is from.

Only use real news outlets, official pollster releases, and established election forecasters (Cook Political Report, Sabato's Crystal Ball, RealClearPolling, Decision Desk HQ, 270toWin) as sources. Skip social media posts, generic ranking/demographic sites, and opinion blogs entirely -- don't include them as sources at all, even if they show up in search.

Also report this state's Cook Partisan Voting Index (the STATEWIDE figure, not a single congressional district's) as a separate structural data point -- do not list PVI as if it were one of the current-race sources above.

Respond with ONLY a single JSON object, no markdown fences, no preamble, matching this schema:

{{
  "state": "<state name>",
  "reasoning": "<2-3 sentences summarizing what you found>",
  "cook_partisan_voting_index": {{"party": "D" | "R" | "EVEN", "percentage_points": <float>}},
  "sources": [
    {{
      "name": "<publication/outlet name>",
      "link": "<direct URL>",
      "race_type": {valid_race_types_pipes},
      "party": "D" | "R" | "EVEN",
      "margin": <float, non-negative or 0 if rating/context>,
      "details": "<one sentence on what this source found>",
      "date_range": "<e.g. 'July 15-17, 2026'>"
    }}
  ]
}}
"""


def build_user_prompt(state: str, mode: str) -> str:
    today = date.today().isoformat()
    race_description = _RACE_DESCRIPTIONS[mode]
    return (
        f"Today's date is {today}. What is the current margin for {race_description} "
        f"in {state} (D+ or R+), based on polling/news from the last {RECENCY_DAYS} "
        f"days? Your training data has a cutoff and cannot contain anything about "
        f"races or polling after that cutoff -- search first."
    )


@dataclass
class SourceEntry:
    name: str
    link: str
    race_type: str = "other_context"
    party: Optional[str] = None
    margin: Optional[float] = None
    details: str = ""
    date_range: str = ""
    domain: Optional[str] = None
    verified: bool = False


@dataclass
class StateVerdict:
    state: str
    mode: str
    lean: str
    confidence: float
    strength_label: str
    net_margin: float
    reasoning: str
    as_of_date: str
    cook_pvi: dict = field(default_factory=dict)
    sources: list = field(default_factory=list)


def _domain_from_url(url: str) -> str:
    m = re.match(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1) if m else url


def _validate_pvi(raw: dict) -> dict:
    raw = raw or {}
    party = raw.get("party", "EVEN")
    if party not in ("D", "R", "EVEN"):
        party = "EVEN"
    try:
        points = float(raw.get("percentage_points", 0.0))
    except (TypeError, ValueError):
        points = 0.0
    return {"party": party, "percentage_points": max(0.0, points)}


def _parse_json_verdict(raw_text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def _looks_like_rating(details: str, name: str) -> bool:
    text = f"{name} {details}".lower()
    return any(
        phrase in text
        for phrase in [
            "solid democratic",
            "solid republican",
            "likely democratic",
            "likely republican",
            "lean democratic",
            "lean republican",
            "safe democratic",
            "safe republican",
            "tilt democratic",
            "tilt republican",
            "toss-up",
            "toss up",
        ]
    )


def _extract_sources(parsed: dict, real_citations: list, mode: str) -> list:
    real_citations_set = set(real_citations or [])
    valid_race_types = _RACE_TARGETS[mode] | {"other_context"}
    entries = []

    for raw in parsed.get("sources", []) or []:
        if not isinstance(raw, dict):
            continue

        link = raw.get("link")
        if not link:
            continue

        party = raw.get("party")
        if party not in ("D", "R", "EVEN", None):
            party = None

        margin = raw.get("margin")
        try:
            margin = float(margin) if margin is not None else None
            if margin is not None:
                margin = max(0.0, margin)
        except (TypeError, ValueError):
            margin = None

        race_type = raw.get("race_type", "other_context")
        if race_type not in valid_race_types:
            race_type = "other_context"

        name = raw.get("name", "") or _domain_from_url(link)
        details = raw.get("details", "") or ""

        entries.append(SourceEntry(
            name=name,
            link=link,
            race_type=race_type,
            party=party,
            margin=margin,
            details=details,
            date_range=raw.get("date_range", "") or "",
            domain=_domain_from_url(link),
            verified=link in real_citations_set,
        ))

    return entries


def assess_state(state: str, client: Perplexity, mode: str = MODE_SENATE_PRESIDENTIAL) -> StateVerdict:
    if mode not in _RACE_TARGETS:
        raise ValueError(f"Unknown mode: {mode!r}. Must be one of {list(_RACE_TARGETS)}")

    valid_race_types = sorted(_RACE_TARGETS[mode] | {"other_context"})

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _build_system_prompt(mode)},
            {"role": "user", "content": build_user_prompt(state, mode)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "state_verdict",
                "schema": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string"},
                        "reasoning": {"type": "string"},
                        "cook_partisan_voting_index": {
                            "type": "object",
                            "properties": {
                                "party": {"type": "string", "enum": ["D", "R", "EVEN"]},
                                "percentage_points": {"type": "number"},
                            },
                            "required": ["party", "percentage_points"],
                        },
                        "sources": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "link": {"type": "string"},
                                    "race_type": {"type": "string", "enum": valid_race_types},
                                    "party": {"type": "string", "enum": ["D", "R", "EVEN"]},
                                    "margin": {"type": "number"},
                                    "details": {"type": "string"},
                                    "date_range": {"type": "string"},
                                },
                                "required": ["name", "link", "race_type", "details", "date_range"],
                            },
                        },
                    },
                    "required": ["state", "reasoning", "cook_partisan_voting_index", "sources"],
                },
            },
        },
        search_recency_filter="month",
    )

    raw_text = response.choices[0]["message"]["content"].strip()
    parsed = _parse_json_verdict(raw_text)

    real_citations = getattr(response, "citations", []) or []
    sources = _extract_sources(parsed, real_citations, mode)
    cook_pvi = _validate_pvi(parsed.get("cook_partisan_voting_index"))

    computed = compute_lean_from_sources(
        [asdict(s) for s in sources],
        target_race_types=_RACE_TARGETS[mode],
        cook_pvi=cook_pvi,
    )

    return StateVerdict(
        state=parsed.get("state", state),
        mode=mode,
        lean=computed["lean"],
        confidence=computed["confidence"],
        strength_label=computed["strength_label"],
        net_margin=computed["net_margin"],
        reasoning=parsed.get("reasoning", ""),
        as_of_date=datetime.now().isoformat(timespec="seconds"),
        cook_pvi=cook_pvi,
        sources=[asdict(s) for s in sources],
    )