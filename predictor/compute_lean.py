from typing import Optional, List, Dict, Any

TOSSUP_THRESHOLD = 5.0
TILT_THRESHOLD = 10.0
LEAN_THRESHOLD = 20.0
CONFIDENCE_SATURATION = 25.0

NOMINAL_DIRECTIONAL_WEIGHT = 2.0

TARGET_RACE_TYPES_DEFAULT = {"senate", "presidential"}


def _rating_strength(text: str) -> Optional[float]:
    """
    Return a signed strength based on rating language.
    Positive = D, negative = R, None = no rating detected.
    """
    t = (text or "").lower()

    # Democratic ratings
    if "safe democratic" in t or "solid democratic" in t:
        return 20.0
    if "likely democratic" in t:
        return 10.0
    if "lean democratic" in t or "tilt democratic" in t:
        return 5.0

    # Republican ratings
    if "safe republican" in t or "solid republican" in t:
        return -20.0
    if "likely republican" in t:
        return -10.0
    if "lean republican" in t or "tilt republican" in t:
        return -5.0

    # Explicit toss-up
    if "toss-up" in t or "toss up" in t:
        return 0.0

    return None


def _source_direction(source: Dict[str, Any]) -> Optional[str]:
    party = source.get("party")
    if party in ("D", "R"):
        return party
    return None


def _source_weight(source: Dict[str, Any]) -> float:
    """
    Numeric weight for this source:
    - real margin > 0 -> use that
    - else try to infer from rating language
    - else 0
    """
    margin = source.get("margin")
    if margin is not None and margin > 0:
        return float(margin)

    details = f"{source.get('name', '')} {source.get('details', '')}".lower()
    rating = _rating_strength(details)
    if rating is not None:
        return abs(rating)

    return 0.0


def _best_rating_label(sources: List[Dict[str, Any]]) -> Optional[str]:
    """
    Return the strongest rating label found among sources, or None.
    Prioritizes explicit rating language in details/name.
    """
    best = None
    order = [
        "safe democratic", "solid democratic",
        "safe republican", "solid republican",
        "likely democratic", "likely republican",
        "lean democratic", "lean republican",
        "tilt democratic", "tilt republican",
        "toss-up", "toss up",
    ]

    for s in sources:
        text = f"{s.get('name', '')} {s.get('details', '')}".lower()
        for label in order:
            if label in text:
                if best is None or order.index(label) < order.index(best):
                    best = label

    return best


def _compute_confidence(
    net_margin: float,
    d_articles: int,
    r_articles: int,
    best_rating: Optional[str],
) -> float:
    abs_margin = abs(net_margin)

    # Margin-based component (0..1)
    if abs_margin < TOSSUP_THRESHOLD:
        margin_conf = 0.5 * (abs_margin / TOSSUP_THRESHOLD)  # 0..0.5
    else:
        span = CONFIDENCE_SATURATION - TOSSUP_THRESHOLD
        progress = min(1.0, (abs_margin - TOSSUP_THRESHOLD) / span)
        margin_conf = 0.5 + 0.5 * progress  # 0.5..1.0

    # Directional agreement component (0..0.5)
    total_articles = d_articles + r_articles
    if total_articles == 0:
        clarity_conf = 0.0
    else:
        max_side = max(d_articles, r_articles)
        clarity_conf = 0.5 * (max_side / total_articles)

    raw_conf = margin_conf + clarity_conf

    # Rating floor
    rating_floor = 0.0
    if best_rating:
        if "solid" in best_rating or "safe" in best_rating:
            rating_floor = 0.8
        elif "likely" in best_rating:
            rating_floor = 0.7
        elif "lean" in best_rating or "tilt" in best_rating:
            rating_floor = 0.6

    final_conf = max(raw_conf, rating_floor)
    return min(1.0, final_conf)


def compute_lean_from_sources(
    sources: List[Dict[str, Any]],
    target_race_types: Optional[set] = None,
    cook_pvi: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if target_race_types is None:
        target_race_types = TARGET_RACE_TYPES_DEFAULT

    # Use only target-race sources if available
    active = [s for s in sources if s.get("race_type") in target_race_types]

    # Fallback to PVI-like other_context if no target sources
    if not active and cook_pvi:
        party = cook_pvi.get("party", "EVEN")
        points = float(cook_pvi.get("percentage_points", 0.0) or 0.0)
        if party in ("D", "R") and points > 0:
            active = [{"party": party, "margin": points, "details": "Cook PVI"}]

    if not active:
        return {
            "lean": "Toss-up",
            "confidence": 0.0,
            "net_margin": 0.0,
            "strength_label": "Toss-up",
            "d_total": 0.0,
            "r_total": 0.0,
            "source_count": 0,
        }

    d_margin = 0.0
    r_margin = 0.0
    d_articles = 0
    r_articles = 0
    counted = 0

    for s in active:
        party = _source_direction(s)
        if party not in ("D", "R"):
            continue

        counted += 1
        weight = _source_weight(s)

        if party == "D":
            d_articles += 1
            d_margin += weight
        else:
            r_articles += 1
            r_margin += weight

    net_margin = d_margin - r_margin
    abs_margin = abs(net_margin)

    # Determine lean
    if abs_margin >= TOSSUP_THRESHOLD:
        lean = "D" if net_margin > 0 else "R"
    elif d_articles > r_articles:
        lean = "D"
    elif r_articles > d_articles:
        lean = "R"
    else:
        lean = "Toss-up"

    # Strength label
    if abs_margin >= TOSSUP_THRESHOLD:
        if abs_margin < TILT_THRESHOLD:
            strength_label = "Tilt"
        elif abs_margin < LEAN_THRESHOLD:
            strength_label = "Lean"
        else:
            strength_label = "Strong"
    else:
        if d_articles == r_articles:
            strength_label = "Toss-up"
        else:
            strength_label = "Tilt"

    best_rating = _best_rating_label(active)
    confidence = _compute_confidence(net_margin, d_articles, r_articles, best_rating)

    return {
        "lean": lean,
        "confidence": round(confidence, 3),
        "net_margin": round(net_margin, 2),
        "strength_label": strength_label,
        "d_total": round(d_margin, 2),
        "r_total": round(r_margin, 2),
        "source_count": counted,
    }