import json
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import asdict
 
from flask import Flask, jsonify, abort
from flask_cors import CORS
 
from google import genai
 
from predictor import assess_state, StateVerdict
 
 
app = Flask(__name__)
CORS(app)
 
CACHE_DIR = Path("cache")
CACHE_MAX_AGE_HOURS = 24
API_KEY_FILE = Path("api_key.txt")
 
ABBREVIATION_TO_STATE_NAME = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "Washington DC",
}
 
_client = None
 
 
def get_client():

    global _client
    if _client is None:
        if not API_KEY_FILE.exists():
            raise RuntimeError(
                f"{API_KEY_FILE} not found. Create it with your Gemini API key inside."
            )
        api_key = API_KEY_FILE.read_text().strip()
        _client = genai.Client(api_key=api_key)
    return _client
 
 
def _cache_path(abbr: str) -> Path:
    return CACHE_DIR / f"{abbr.upper()}.json"
 
 
def _read_cache(abbr: str) -> dict | None:
    path = _cache_path(abbr)
    print(f"DEBUG: checking path {path.resolve()}, exists={path.exists()}")
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"DEBUG: JSON parse failed: {e}")
        return None

    try:
        cached_at = datetime.fromisoformat(data.get("_cached_at", ""))
    except ValueError as e:
        print(f"DEBUG: _cached_at parse failed: {e}, raw value was {data.get('_cached_at')!r}")
        return None

    age = datetime.now() - cached_at
    if age > timedelta(hours=CACHE_MAX_AGE_HOURS):
        print(f"DEBUG: cache too old, age={age}")
        return None

    return data
 
 
def _write_cache(abbr: str, verdict_dict: dict) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    verdict_dict["_cached_at"] = datetime.now().isoformat()
    _cache_path(abbr).write_text(json.dumps(verdict_dict, indent=2))
 
 
def _assess_and_cache(abbr: str) -> dict:
    state_name = ABBREVIATION_TO_STATE_NAME.get(abbr.upper())
    if not state_name:
        abort(404, description=f"Unknown state abbreviation: {abbr}")
 
    client = get_client()
    verdict: StateVerdict = assess_state(state_name, client)
 
    result = asdict(verdict)
    result["abbreviation"] = abbr.upper()
 
    _write_cache(abbr, result)
    return result
 
 
@app.route("/api/state/<abbr>")
def get_state(abbr):
    cached = _read_cache(abbr)
    if cached:
        return jsonify(cached)
 
    try:
        result = _assess_and_cache(abbr)
    except RuntimeError as e:
        abort(500, description=str(e))
 
    return jsonify(result)
 
 
@app.route("/api/refresh/<abbr>", methods=["POST"])
def refresh_state(abbr):
    """Force a fresh assessment, bypassing any existing cache."""
    try:
        result = _assess_and_cache(abbr)
    except RuntimeError as e:
        abort(500, description=str(e))
 
    return jsonify(result)
 
 
@app.route("/api/states")
def get_all_states():
    """
    Returns all 50 states + DC. Uses cache where available; only calls the
    model for states with no fresh cache entry. NOTE: on a fully cold cache,
    this will make up to 51 sequential agentic calls -- expect this to take
    a while and to use real API quota. Prefer warming the cache incrementally
    via /api/state/<abbr> rather than hitting this cold.
    """
    results = {}
    for abbr in ABBREVIATION_TO_STATE_NAME:
        cached = _read_cache(abbr)
        if cached:
            results[abbr] = cached
            continue
 
        try:
            results[abbr] = _assess_and_cache(abbr)
        except RuntimeError as e:
            abort(500, description=str(e))
 
    return jsonify(results)
 
 
if __name__ == "__main__":
    app.run(debug=True, port=8080)