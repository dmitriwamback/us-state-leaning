TOSSUP_THRESHOLD = 5.0
TILT_THRESHOLD = 10.0
LEAN_THRESHOLD = 20.0
CONFIDENCE_SATURATION = 25.0
 
# Maximum nominal contribution a qualitative (non-numeric) source can make,
# achieved only at lean_confidence=1.0 -- a very authoritative, unambiguous
# qualitative rating (e.g. "Cook rates this solidly Democratic") should be
# able to count for roughly as much as a real ~5-point poll margin; a weak
# or ambiguous qualitative signal should count for much less.
NOMINAL_MAX_WEIGHT = 5.0
 
TARGET_RACE_TYPES_DEFAULT = {"senate", "presidential"}
 
 
def _source_weight(source: dict, target_race_types: set) -> float:
 
    party = source.get("party")
    if party not in ("D", "R"):
        return 0.0
 
    margin = source.get("margin")
    if margin is not None and margin > 0:
        return abs(margin)
 
    lean_confidence = source.get("lean_confidence")
    if lean_confidence is not None and lean_confidence > 0:
        return min(1.0, lean_confidence) * NOMINAL_MAX_WEIGHT
 
    return 0.0
 
 
def _classify_margin(net_margin: float) -> dict:
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
    if target_race_types is None:
        target_race_types = TARGET_RACE_TYPES_DEFAULT
 
    totals = {"D": 0.0, "R": 0.0}
    total_articles = {"D": 0, "R": 0}
    counted = 0
 
    for source in sources:
        party = source.get("party")
        weight = _source_weight(source, target_race_types)
        if weight > 0 and party in ("D", "R"):
            totals[party] += weight
            total_articles[party] += 1
            counted += 1
 
    net_margin = (totals["D"] - totals["R"])
    
    if net_margin > 0:
        if total_articles['D'] > 0:
            net_margin = totals['D']/total_articles['D']
        else:
            net_margin = totals['D']
    else:
        if total_articles['R'] > 0:
            net_margin = -totals['R']/total_articles['R']
        else:
            net_margin = -totals['R']

    classified = _classify_margin(net_margin)
 
    return {
        **classified,
        "d_total": round(totals["D"], 2),
        "r_total": round(totals["R"], 2),
        "source_count": counted,
        "based_on": "sources",
    }
 
 
def compute_lean_from_pvi(cook_pvi: dict) -> dict:
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