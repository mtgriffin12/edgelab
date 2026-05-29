import pytest
from pydantic import ValidationError

from edgelab.candidates.schema import (
    CandidateEvidenceStrength,
    CandidateReason,
    CandidateRiskFlag,
    CandidateRiskFlagType,
    CandidateSource,
    CandidateStatus,
    EquityCandidate,
)


def build_candidate(**overrides: object) -> EquityCandidate:
    data: dict[str, object] = {
        "candidate_id": "spy-research-candidate",
        "symbol": "spy",
        "title": "SPY Research Candidate",
        "status": CandidateStatus.WATCHLIST_ONLY,
        "evidence_strength": CandidateEvidenceStrength.WEAK,
        "candidate_score": 45.0,
        "plain_english_summary": "SPY is worth keeping visible for research only.",
        "what_supports_it": [
            CandidateReason(
                source=CandidateSource.MARKET_DATA_FIXTURE,
                summary="SPY has local sample rows.",
            )
        ],
        "what_is_missing": ["Real historical data."],
        "what_would_change_our_mind": ["The baseline comparison fails."],
    }
    data.update(overrides)
    return EquityCandidate(**data)


def test_candidate_normalizes_symbol() -> None:
    candidate = build_candidate(symbol=" aapl ")

    assert candidate.symbol == "AAPL"


def test_candidate_requires_machine_friendly_id() -> None:
    with pytest.raises(ValidationError, match="machine-friendly"):
        build_candidate(candidate_id="Bad ID")


def test_candidate_score_bounds() -> None:
    with pytest.raises(ValidationError):
        build_candidate(candidate_score=101)


def test_insufficient_evidence_cannot_be_research_candidate() -> None:
    with pytest.raises(ValidationError, match="insufficient evidence"):
        build_candidate(
            status=CandidateStatus.RESEARCH_CANDIDATE,
            evidence_strength=CandidateEvidenceStrength.INSUFFICIENT,
        )


def test_candidate_cannot_allow_real_money() -> None:
    with pytest.raises(ValidationError, match="real-money status"):
        build_candidate(real_money_status="Allowed")


def test_risk_blocked_candidate_requires_risk_flags() -> None:
    with pytest.raises(ValidationError, match="risk flags"):
        build_candidate(status=CandidateStatus.BLOCKED_BY_RISK)


def test_data_quality_blocked_candidate_requires_quality_issues() -> None:
    with pytest.raises(ValidationError, match="quality issues"):
        build_candidate(status=CandidateStatus.BLOCKED_BY_DATA_QUALITY)


def test_candidate_rejects_action_instruction_phrases() -> None:
    with pytest.raises(ValidationError, match="action instructions"):
        build_candidate(plain_english_summary="buy now")


def test_risk_blocked_candidate_accepts_risk_flags() -> None:
    candidate = build_candidate(
        status=CandidateStatus.BLOCKED_BY_RISK,
        risk_flags=[
            CandidateRiskFlag(
                flag_type=CandidateRiskFlagType.REAL_MONEY_NOT_ALLOWED,
                message="Real-money use is not allowed.",
            )
        ],
    )

    assert candidate.status == CandidateStatus.BLOCKED_BY_RISK
