"""
predictor.py

Agentic per-state political lean assessment using Gemini + Google Search grounding.

Given a US state, uses Gemini with the Google Search grounding tool to find
current polling, recent statewide election results, demographic trends, and
fundraising signals, then produces a structured "current lean" verdict with
real sources (extracted from the actual grounding metadata Gemini used, not
self-reported by the model).

Usage:
    export GEMINI_API_KEY=...
    python predictor.py "Texas"
"""

import sys
import json
import re
from datetime import date, datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
 
from google import genai
from google.genai import types
 
 
MODEL = "gemini-3.5-flash"
RECENCY_DAYS = 45 # sources older than this are treated as 'outdated'
 
 
@dataclass
class Source:
    title: str
    url: str
    domain: Optional[str] = None
 
 
@dataclass
class StateVerdict:
    state: str
    lean: str               # "D", "R", or "Toss-up"
    confidence: float       # 0.0 - 1.0, distance from 50/50
    basis: str              # "current_polling" | "midterm_swing" | "historical_baseline"
    reasoning: str
    as_of_date: str
    sources: list = field(default_factory=list)
 
 

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
3. Prioritize sources published within the last {recency_days} days. Older sources may \
only be used for historical baseline context, NEVER as evidence of current lean.
4. Only fall back to basis="historical_baseline" (using the most recent prior \
election results) if steps 1-2, using real candidate names, genuinely turn up no \
polling or news from the last {recency_days} days. Set confidence based on how \
lopsided that historical baseline actually is, NOT simply low because it's a \
fallback:
   - If prior results show a landslide margin (e.g. 15+ points) with no signal of \
change, confidence should be HIGH (0.7-0.9) -- the absence of competitive news is \
itself evidence the race isn't close.
   - If prior results were close (single digits) or there's reason to think the \
landscape may have shifted, confidence should be LOW-MODERATE, reflecting genuine \
uncertainty about the current state.
5. Do not average toward the "usual" outcome for a state out of habit — if evidence is \
lopsided, say so; if evidence is genuinely mixed, use lean="Toss-up".
6. Confidence should reflect how lopsided the CURRENT evidence is, not how safe the \
seat has historically been (except where rule 4 applies to a historical_baseline \
fallback).
7. After researching, respond with ONLY a single JSON object, no markdown fences, no \
preamble, matching exactly this schema:

{{
  "state": "<state name>",
  "lean": "D" | "R" | "Toss-up",
  "confidence": <float 0.0 to 1.0>,
  "basis": "current_polling" | "midterm_swing" | "historical_baseline",
  "reasoning": "<2-3 sentences, plain language, referencing specific numbers you found>"
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
 
 
def _domain_from_url(url: str) -> str:
    m = re.match(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1) if m else url
 
 
def _extract_sources(response) -> list[Source]:

    sources: list[Source] = []
    seen_urls = set()
 
    steps = getattr(response, "steps", None) or []
    for step in steps:
        if getattr(step, "type", None) != "model_output":
            continue
 
        content_blocks = getattr(step, "content", None) or []
        for block in content_blocks:
            if getattr(block, "type", None) != "text":
                continue
 
            annotations = getattr(block, "annotations", None) or []
            for ann in annotations:
                if getattr(ann, "type", None) != "url_citation":
                    continue
 
                url = getattr(ann, "url", None)
                title = getattr(ann, "title", "") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                sources.append(Source(title=title, url=url, domain=_domain_from_url(url)))
 
    return sources
 
 
def _parse_json_verdict(raw_text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)
 
 
def assess_state(state: str, client: "genai.Client") -> StateVerdict:
    response = client.interactions.create(
        model=MODEL,
        input=f"{SYSTEM_PROMPT}\n\n{build_user_prompt(state)}",
        tools=[{"type": "google_search"}],
    )
 
    raw_text = (response.output_text or "").strip()
    sources = _extract_sources(response)
 
    try:
        parsed = _parse_json_verdict(raw_text)
    except (json.JSONDecodeError, AttributeError) as e:
        raise ValueError(
            f"Could not parse model output as JSON for state={state!r}.\n"
            f"Raw output was:\n{raw_text}\n\nError: {e}"
        )
 
    verdict = StateVerdict(
        state=parsed.get("state", state),
        lean=parsed.get("lean", "Toss-up"),
        confidence=float(parsed.get("confidence", 0.0)),
        basis=parsed.get("basis", "historical_baseline"),
        reasoning=parsed.get("reasoning", ""),
        as_of_date=datetime.now().isoformat(timespec="seconds"),
        sources=[asdict(s) for s in sources],
    )
    return verdict
 
 
def main():
    if len(sys.argv) < 2:
        print("Usage: python predictor.py \"<State Name>\"")
        sys.exit(1)
 
    state = " ".join(sys.argv[1:])
    with open('api_key.txt', 'r+') as file:
        api_key = file.read()
 
    client = genai.Client(api_key=api_key)
 
    print(f"Assessing current lean for: {state} ...")
    verdict = assess_state(state, client)
 
    print(json.dumps(asdict(verdict), indent=2))
 
 
if __name__ == "__main__":
    main()