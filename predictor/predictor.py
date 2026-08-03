import os
import json
import re
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import date

from perplexity import Perplexity  # SDK name may vary

MODEL = "sonar-pro"
RECENCY_DAYS = 45

SYSTEM_PROMPT = """You are a political data analyst. You will be asked to assess \
the CURRENT partisan lean of a US state for federal elections (Senate/Presidential), \
based only on what you find via search — not on your own prior/training knowledge of \
how the state "usually" votes.

Rules you MUST follow:

1. FIRST, identify who is actually on the ballot: search for the current Senate \
and/or gubernatorial candidates/incumbents for this state (e.g. "[state] senate \
race 2026 candidates"). You cannot judge current lean without knowing who is \
running.

2. THEN, using the specific candidate names you just found, search for recent polling \
and news about them by name (e.g. "[candidate name] poll [current year]", \
"[candidate A] vs [candidate B] poll"). A single generic query like "[state] lean" \
is NOT an adequate search -- it will not surface named-candidate polling and should \
never be your only search.

3. SOURCE QUALITY -- only treat the following as valid evidence: major news outlets \
(AP, Reuters, NYT, Washington Post, NPR, major regional papers), official pollster \
releases, established election forecasters (Cook Political Report, Sabato's Crystal \
Ball, RealClearPolling, Decision Desk HQ, 270toWin), and official election data \
sources (Ballotpedia, state election board sites). NEVER use social media posts \
(Facebook, X/Twitter, YouTube, Reddit, Instagram), generic demographic/ranking \
aggregator sites (e.g. worldpopulationreview-style pages), or partisan opinion blogs \
as evidence for current lean -- these may appear in search results but must be \
ignored, not cited.

4. CROSS-REFERENCE before finalizing: check at least two independent \
forecasters/polling averages (e.g. Cook Political Report AND RealClearPolling AND/OR \
Sabato's Crystal Ball) where available. If they meaningfully disagree with each \
other, that disagreement is itself evidence of a genuine toss-up (lean="Toss-up", \
lower confidence) -- do not just adopt whichever single source you happened to read \
first. Note in your reasoning if forecasters disagree.

5. Prioritize sources published within the last {recency_days} days for evidence of \
CURRENT lean. Older sources may only be used for historical baseline context, NEVER \
as evidence of current lean.

6. BASIS LABELING -- distinguish these three cases correctly:
   - "current_polling": you found actual head-to-head polling numbers between named \
candidates within the last {recency_days} days.
   - "midterm_swing": you found current-cycle news (primary results, candidate \
announcements, fundraising totals, forecaster ratings) within the last \
{recency_days} days, but no direct head-to-head polling yet. Do NOT mislabel this \
as "historical_baseline" just because a specific poll number wasn't found -- if you \
have current-cycle information, use midterm_swing and explain what that current \
information suggests about momentum.
   - "historical_baseline": you genuinely found NO current-cycle information at all \
(steps 1-2, with real candidate names, turned up nothing from the last \
{recency_days} days), so you are relying entirely on the most recent prior election \
results.

7. For a "historical_baseline" verdict, set confidence based on how lopsided that \
historical baseline actually is, NOT simply low because it's a fallback:
   - If prior results show a landslide margin (e.g. 15+ points) with no signal of \
change, confidence should be HIGH (0.7-0.9) -- the absence of competitive news is \
itself evidence the race isn't close.
   - If prior results were close (single digits) or there's reason to think the \
landscape may have shifted, confidence should be LOW-MODERATE, reflecting genuine \
uncertainty about the current state.

8. Do not average toward the "usual" outcome for a state out of habit -- if evidence \
is lopsided, say so; if evidence is genuinely mixed or forecasters disagree \
(see rule 4), use lean="Toss-up".

9. Confidence should reflect how lopsided the CURRENT evidence is, not how safe the \
seat has historically been (except where rule 7 applies to a historical_baseline \
fallback).

10. Also report a current_margin -- the actual current point spread between the two \
leading candidates, based on the polling/news you found in steps 1-2 (e.g. if \
Talarico leads Paxton 45% to 40%, that's a 5-point Democratic margin, regardless of \
Texas's historical/structural lean). This is DIFFERENT from Cook PVI (a stable \
structural baseline) -- current_margin reflects THIS race, right now, and can point \
in the opposite direction from PVI entirely (a Democrat leading in a structurally \
red state, or vice versa). If you only have historical_baseline (no current \
race data), report the most recent prior election's actual margin instead, and note \
in reasoning that this is a historical, not current, figure. Report as a party \
("D", "R", or "EVEN" for a tied/0-point race) and percentage_points (the point \
spread, always non-negative).

11. SELF-CONSISTENCY (important): current_margin and cook_partisan_voting_index \
must NOT be numbers you compute silently in your head -- the specific figures you \
report in these fields MUST also be explicitly stated or directly derivable from \
what you wrote in "reasoning". If reasoning says "45% to 40%", current_margin must \
be party=D (winner), percentage_points=5 (not some other number you didn't \
mention). If you cannot point to where a margin number came from in your own \
reasoning text, you have not actually grounded it -- go back and either find the \
real figure or lower confidence and note the uncertainty explicitly, rather than \
reporting a number your reasoning doesn't support.

12. Also report this state's Cook Partisan Voting Index (PVI) -- search for it \
specifically (e.g. "[state] Cook PVI" or check Wikipedia's Cook Partisan Voting \
Index page/Cook Political Report directly). PVI is a stable structural metric \
(based on the last two presidential elections) that changes rarely, so accuracy \
here matters -- do not guess. IMPORTANT: Cook publishes PVI per CONGRESSIONAL \
DISTRICT, not as one simple state-level number on most pages you'll find -- a \
single district's PVI (e.g. one rural conservative district in an otherwise \
Democratic state, or vice versa) is NOT the state's overall PVI. Make sure you \
are reporting the STATEWIDE PVI specifically (Cook Political Report publishes \
this separately from district-level data, e.g. "How the States Have Shifted: \
Statewide Cook PVI"), not a single district's figure. Report it as a party \
("D", "R", or "EVEN" for a PVI of exactly 0) and a percentage_points value (the \
point spread, always non-negative; use 0 for EVEN).

13. After researching, respond with ONLY a single JSON object, no markdown fences, \
no preamble, matching exactly this schema:

{{
  "state": "<state name>",
  "lean": "D" | "R" | "Toss-up",
  "confidence": <float 0.0 to 1.0>,
  "basis": "current_polling" | "midterm_swing" | "historical_baseline",
  "reasoning": "<2-3 sentences, plain language, referencing specific numbers you found>",
  "current_margin": {{
    "party": "D" | "R" | "EVEN",
    "percentage_points": <float, non-negative>
  }},
  "cook_partisan_voting_index": {{
    "party": "D" | "R" | "EVEN",
    "percentage_points": <float, non-negative>
  }}
}}
""".format(recency_days=RECENCY_DAYS)


def build_user_prompt(state: str) -> str:
    today = date.today().isoformat()
    return (
        f"Today's date is {today}. You must search for information to answer this — "
        f"your training data has a cutoff date and CANNOT contain any information "
        f"about races, candidates, or polling after that cutoff. Assessing {state}'s "
        f"current lean from memory alone would be answering with stale, potentially "
        f"wrong information. Search first, then assess the current federal-election "
        f"partisan lean for {state}, following the rules in your system instructions."
    )


@dataclass
class Source:
    title: str
    url: str
    domain: Optional[str] = None


@dataclass
class StateVerdict:
    state: str
    lean: str
    confidence: float
    basis: str
    reasoning: str
    as_of_date: str
    sources: list = field(default_factory=list)
    current_margin: dict = field(default_factory=dict)  # {"party": "D"|"R"|"EVEN", "percentage_points": float} -- THIS race, right now
    cook_pvi: dict = field(default_factory=dict)  # {"party": "D"|"R"|"EVEN", "percentage_points": float} -- structural baseline


# Domains excluded at the retrieval level, not just via prompt instruction --
# this is a stronger guarantee than asking the model to "ignore" junk sources,
# since Perplexity's search_domain_filter can exclude them before the model
# ever sees them. Verify the exact parameter name/behavior against Perplexity's
# current API docs -- this list is a best-effort starting point.
EXCLUDED_DOMAINS = [
    "facebook.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "reddit.com",
    "instagram.com",
    "tiktok.com",
]


def _domain_from_url(url: str) -> str:
    m = re.match(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1) if m else url


def _extract_sources(response) -> list[Source]:
    sources = []
    for url in getattr(response, "citations", []):
        sources.append(Source(title=url, url=url, domain=_domain_from_url(url)))
    return sources


def _parse_json_verdict(raw_text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def _validate_margin(raw: dict) -> dict:
    """Shared validator for both current_margin and cook_pvi -- same shape,
    same failure modes, so one function handles both rather than duplicating
    the same defensive logic twice."""
    raw = raw or {}
    party = raw.get("party", "EVEN")
    if party not in ("D", "R", "EVEN"):
        party = "EVEN"
    try:
        points = float(raw.get("percentage_points", 0.0))
    except (TypeError, ValueError):
        points = 0.0
    points = max(0.0, points)
    return {"party": party, "percentage_points": points}


def assess_state(state: str, client: Perplexity) -> StateVerdict:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(state)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "state_verdict",
                "schema": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string"},
                        "lean": {"type": "string", "enum": ["D", "R", "Toss-up"]},
                        "confidence": {"type": "number"},
                        "basis": {
                            "type": "string",
                            "enum": ["current_polling", "midterm_swing", "historical_baseline"],
                        },
                        "reasoning": {"type": "string"},
                        "current_margin": {
                            "type": "object",
                            "properties": {
                                "party": {"type": "string", "enum": ["D", "R", "EVEN"]},
                                "percentage_points": {"type": "number"},
                            },
                            "required": ["party", "percentage_points"],
                        },
                        "cook_partisan_voting_index": {
                            "type": "object",
                            "properties": {
                                "party": {"type": "string", "enum": ["D", "R", "EVEN"]},
                                "percentage_points": {"type": "number"},
                            },
                            "required": ["party", "percentage_points"],
                        },
                    },
                    "required": [
                        "state", "lean", "confidence", "basis", "reasoning",
                        "current_margin", "cook_partisan_voting_index",
                    ],
                },
            },
        },
        search_recency_filter="month",
        search_domain_filter=[f"-{d}" for d in EXCLUDED_DOMAINS],  # "-" prefix = exclude, per Perplexity convention
    )

    raw_text = response.choices[0]["message"]["content"].strip()

    parsed = _parse_json_verdict(raw_text)
    sources = _extract_sources(response)

    current_margin = _validate_margin(parsed.get("current_margin"))
    cook_pvi = _validate_margin(parsed.get("cook_partisan_voting_index"))

    return StateVerdict(
        state=parsed.get("state", state),
        lean=parsed.get("lean", "Toss-up"),
        confidence=float(parsed.get("confidence", 0.0)),
        basis=parsed.get("basis", "historical_baseline"),
        reasoning=parsed.get("reasoning", ""),
        as_of_date=datetime.now().isoformat(timespec="seconds"),
        sources=[asdict(s) for s in sources],
        current_margin=current_margin,
        cook_pvi=cook_pvi,
    )