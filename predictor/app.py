import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import asdict

from flask import Flask, jsonify, abort
from flask_cors import CORS

from predictor import assess_state, StateVerdict
from perplexity import Perplexity


app = Flask(__name__)
CORS(app)

CACHE_DIR = Path("cache")
CACHE_MAX_AGE_HOURS = 24 * 7
API_KEY_FILE = Path("api_key.txt")

ABBREVIATION_TO_STATE_NAME = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "ME-1": "Maine-1", "ME-2": "Maine-2",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NE-1": "Nebraska-1", "NE-2": "Nebraska-2", "NE-3": "Nebraska-3",
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
        _client = Perplexity(api_key=api_key)
    return _client


def _cache_path(abbr: str) -> Path:
    return CACHE_DIR / f"{abbr.upper()}.json"


def _read_cache(abbr: str) -> dict | None:
    path = _cache_path(abbr)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    try:
        cached_at = datetime.fromisoformat(data.get("_cached_at", ""))
    except ValueError:
        return None

    if datetime.now() - cached_at > timedelta(hours=CACHE_MAX_AGE_HOURS):
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


@app.route("/api/cached")
def get_cached_states():
    results = {}
    for abbr in ABBREVIATION_TO_STATE_NAME:
        cached = _read_cache(abbr)
        if cached:
            results[abbr] = cached
    return jsonify(results)


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
    try:
        result = _assess_and_cache(abbr)
    except RuntimeError as e:
        abort(500, description=str(e))

    return jsonify(result)


@app.route("/api/states")
def get_all_states():
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