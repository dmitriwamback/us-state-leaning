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
 
 
MODEL = "antigravity-preview-05-2026"
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
1. Prioritize sources published within the last {recency_days} days. Older sources may \
only be used for historical baseline context, NEVER as evidence of current lean.
2. If you cannot find any recent (last {recency_days} days) polling or news for this \
state's federal races, say so explicitly and fall back to basis="historical_baseline" \
using the most recent prior election results you can find, with LOW confidence.
3. Do not average toward the "usual" outcome for a state out of habit — if evidence is \
lopsided, say so; if evidence is genuinely mixed, use lean="Toss-up".
4. Confidence should reflect how lopsided the CURRENT evidence is, not how safe the seat \
has historically been.
5. Search using explicit, dated queries (include the current year, candidate names if \
known, and terms like "poll" or "special election") rather than vague queries like \
"[state] lean" which tend to surface old or low-quality pages.
6. After researching, respond with ONLY a single JSON object, no markdown fences, no \
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
        f"Today's date is {today}. Assess the current federal-election partisan lean "
        f"for the state of {state}. Search for recent polling, recent statewide election "
        f"results, and any major fundraising or news signal that would move the needle. "
        f"Then output the JSON verdict as instructed."
    )
 
 
def _domain_from_url(url: str) -> str:
    m = re.match(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1) if m else url
 
 
def _extract_sources(response) -> list[Source]:
    """Pull the real grounding sources Gemini's search tool actually used."""
    sources: list[Source] = []
    seen_urls = set()
 
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        grounding_metadata = getattr(candidate, "grounding_metadata", None)
        if not grounding_metadata:
            continue
 
        chunks = getattr(grounding_metadata, "grounding_chunks", None) or []
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            if not web:
                continue
            url = getattr(web, "uri", None)
            title = getattr(web, "title", "") or ""
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            sources.append(Source(title=title, url=url, domain=_domain_from_url(url)))
 
    return sources
 
 
def _parse_json_verdict(raw_text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)
 
 
def assess_state(state: str, client: "genai.Client") -> StateVerdict:
    grounding_tool = types.Tool(google_search=types.GoogleSearch())
 
    response = client.interactions.create(
        model="gemini-3.5-flash",
        input=f"""
        {SYSTEM_PROMPT}
        {build_user_prompt(state)}
        """,
        environment="remote",
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