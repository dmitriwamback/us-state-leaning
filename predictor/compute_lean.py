"""
compute_lean.py

Deterministically derives lean + confidence from the per-source party/margin
data the AI already collected, instead of trusting the model's own
top-level "lean"/"confidence" synthesis (which has proven unreliable --
e.g. calling Oregon a toss-up or Texas "firm red" despite its own source
list showing a close race).
"""

from typing import Optional


# Net margin thresholds (in points). Tunable.
TOSSUP_THRESHOLD = 5.0     # |net margin| below this -> Toss-up
TILT_THRESHOLD = 10.0      # below this (but above TOSSUP) -> weak lean ("Tilt")
LEAN_THRESHOLD = 20.0      # below this (but above TILT) -> moderate lean ("Lean")
# anything >= LEAN_THRESHOLD -> "Strong"/"Solid" lean

# Sources that report a direction but no real number ("favors D", margin=0
# with a non-EVEN party) get a small nominal weight rather than 0, so they
# still nudge the total without pretending to be a precise data point.
NOMINAL_DIRECTIONAL_WEIGHT = 2.0


TARGET_RACE_TYPES_DEFAULT = {"senate", "presidential"}


def _source_weight(source: dict, target_race_types: set) -> float:
    """
    How much this source's margin counts toward its party's bucket.
    - Wrong race_type for the current mode -> 0, regardless of what
      party/margin it reports. A Governor's race source must not
      contaminate a senate_presidential_polling assessment, and vice versa.
    - EVEN or missing margin -> 0 (doesn't push either direction)
    - explicit party + 0 margin ("favors D, no number") -> small nominal weight
    - explicit party + real margin -> that margin's magnitude
    """
    if source.get("race_type") not in target_race_types:
        return 0.0

    party = source.get("party")
    margin = source.get("margin")

    if party not in ("D", "R"):
        return 0.0
    if margin is None:
        return 0.0
    if margin == 0:
        return NOMINAL_DIRECTIONAL_WEIGHT
    return abs(margin)


def _classify_margin(net_margin: float) -> dict:
    """
    Shared classification logic used by both compute_lean_from_sources and
    compute_lean_from_pvi, so both paths apply identical thresholds.
    """
    abs_margin = abs(net_margin)

    if abs_margin < TOSSUP_THRESHOLD:
        lean = "Toss-up"
        strength_label = "Toss-up"
    else:
        lean = "D" if net_margin > 0 else "R"
        if abs_margin < TILT_THRESHOLD:
            strength_label = "Tilt"
        elif abs_margin < LEAN_THRESHOLD:
            strength_label = "Lean"
        else:
            strength_label = "Strong"

    CONFIDENCE_SATURATION = 25.0
    if abs_margin < TOSSUP_THRESHOLD:
        confidence = 0.5 * (abs_margin / TOSSUP_THRESHOLD)
    else:
        span = CONFIDENCE_SATURATION - TOSSUP_THRESHOLD
        progress = min(1.0, (abs_margin - TOSSUP_THRESHOLD) / span)
        confidence = 0.5 + 0.5 * progress

    return {
        "lean": lean,
        "confidence": round(confidence, 3),
        "net_margin": round(net_margin, 2),
        "strength_label": strength_label,
    }


def compute_lean_from_sources(sources: list, target_race_types: set = None) -> dict:
    """
    Returns {"lean": "D"|"R"|"Toss-up", "confidence": float 0-1,
    "net_margin": signed float (positive = D, negative = R),
    "strength_label": "Toss-up"|"Tilt"|"Lean"|"Strong",
    "d_total": float, "r_total": float, "source_count": int,
    "based_on": "sources"}

    target_race_types controls which sources are eligible to count at all --
    defaults to {"senate", "presidential"} for the main federal-lean mode;
    pass {"governor"} when assessing governor_polling mode instead.
    """
    if target_race_types is None:
        target_race_types = TARGET_RACE_TYPES_DEFAULT

    totals = {"D": 0.0, "R": 0.0}
    counted = 0

    for source in sources:
        party = source.get("party")
        weight = _source_weight(source, target_race_types)
        if weight > 0 and party in ("D", "R"):
            totals[party] += weight
            counted += 1

    net_margin = 0
    try:
        net_margin = (totals["D"] - totals["R"]) / counted  # positive = favors D, negative = favors R
    except:
        net_margin = (totals["D"] - totals["R"])

    classified = _classify_margin(net_margin)

    return {
        **classified,
        "d_total": round(totals["D"], 2),
        "r_total": round(totals["R"], 2),
        "source_count": counted,
        "based_on": "sources",
    }


def compute_lean_from_pvi(cook_pvi: dict) -> dict:
    """
    Fallback for when no usable current-race sources exist at all (e.g. a
    quiet state with no recent Senate/Presidential/Governor coverage).
    Rather than reporting a contentless "Toss-up, confidence 0" -- which is
    itself misleading for a state that's actually structurally safe -- use
    the statewide Cook PVI as the basis instead, applying the same
    landslide-confidence logic established for historical_baseline states
    (a lopsided structural lean IS real evidence, even without fresh polling).

    Returns the same shape as compute_lean_from_sources, with
    based_on="cook_pvi_fallback" and source_count=0 so callers can tell
    this was a fallback rather than genuine current-race data.
    """
    cook_pvi = cook_pvi or {}
    party = cook_pvi.get("party", "EVEN")
    points = cook_pvi.get("percentage_points", 0.0) or 0.0

    if party == "D":
        net_margin = points
    elif party == "R":
        net_margin = -points
    else:
        net_margin = 0.0

    classified = _classify_margin(net_margin)

    return {
        **classified,
        "d_total": round(points, 2) if party == "D" else 0.0,
        "r_total": round(points, 2) if party == "R" else 0.0,
        "source_count": 0,
        "based_on": "cook_pvi_fallback",
    }