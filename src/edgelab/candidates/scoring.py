"""Deterministic scoring helpers for research-only equity candidates."""

from __future__ import annotations

from edgelab.candidates.schema import CandidateEvidenceStrength, CandidateStatus


def score_candidate(
    *,
    highest_ranking_score: float,
    support_count: int,
    market_quality_issue_count: int,
    sentiment_quality_issue_count: int,
    risk_flag_count: int,
    sentiment_event_count: int,
) -> float:
    """Return a conservative 0-100 candidate score."""

    score = 20.0
    score += min(highest_ranking_score, 100.0) * 0.42
    score += min(support_count, 5) * 4.0
    if sentiment_event_count >= 2:
        score += 6.0
    elif sentiment_event_count == 1:
        score += 2.0
    score -= market_quality_issue_count * 14.0
    score -= sentiment_quality_issue_count * 6.0
    score -= risk_flag_count * 4.0
    return round(max(0.0, min(100.0, score)), 6)


def evidence_strength_for_score(
    score: float,
    *,
    support_count: int,
    quality_issue_count: int,
    has_unsupported_logic: bool,
) -> CandidateEvidenceStrength:
    """Classify candidate evidence in plain conservative buckets."""

    if has_unsupported_logic or quality_issue_count >= 3 or support_count == 0:
        return CandidateEvidenceStrength.INSUFFICIENT
    if score >= 75:
        return CandidateEvidenceStrength.MODERATE
    if score >= 60:
        return CandidateEvidenceStrength.MIXED
    if score >= 40:
        return CandidateEvidenceStrength.WEAK
    return CandidateEvidenceStrength.INSUFFICIENT


def status_for_candidate(
    score: float,
    evidence_strength: CandidateEvidenceStrength,
    *,
    quality_issue_count: int,
    has_blocking_risk: bool,
) -> CandidateStatus:
    """Choose a research-only candidate status from score and cautions."""

    if quality_issue_count >= 3:
        return CandidateStatus.BLOCKED_BY_DATA_QUALITY
    if has_blocking_risk:
        return CandidateStatus.BLOCKED_BY_RISK
    if evidence_strength == CandidateEvidenceStrength.INSUFFICIENT:
        return CandidateStatus.INSUFFICIENT_EVIDENCE
    if score >= 68:
        return CandidateStatus.RESEARCH_CANDIDATE
    if score >= 50:
        return CandidateStatus.INTERESTING_BUT_INCOMPLETE
    if score >= 35:
        return CandidateStatus.WATCHLIST_ONLY
    return CandidateStatus.INSUFFICIENT_EVIDENCE
