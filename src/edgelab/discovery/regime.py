"""Local scaffold for current-regime fit."""

from edgelab.discovery.schema import CurrentRegimeFit, RegimeFitLabel


def label_for_regime_score(score: int) -> RegimeFitLabel:
    """Return a plain regime-fit label for a 0-10 score."""

    if score <= 0:
        return RegimeFitLabel.INSUFFICIENT_DATA
    if score <= 3:
        return RegimeFitLabel.POOR_FIT
    if score <= 5:
        return RegimeFitLabel.WEAK_FIT
    if score <= 7:
        return RegimeFitLabel.POSSIBLE_FIT
    return RegimeFitLabel.STRONG_FIT


def make_regime_fit(
    score: int,
    plain_english_reason: str,
    matching_conditions: list[str] | None = None,
    missing_conditions: list[str] | None = None,
    caution: str = "Static scaffold only. This does not use live market data.",
) -> CurrentRegimeFit:
    """Create a local static regime-fit record."""

    return CurrentRegimeFit(
        score=score,
        label=label_for_regime_score(score),
        plain_english_reason=plain_english_reason,
        matching_conditions=matching_conditions or [],
        missing_conditions=missing_conditions or [],
        caution=caution,
    )
