"""Deterministic local runner for structured intraday idea batches."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from edgelab.intraday.csv_normalizers import FirstRateLocalCSVHistoricalProvider
from edgelab.intraday.discovery_sprint import DiscoverySprintService
from edgelab.intraday.discovery_sprint_schema import (
    DiscoverySprintClassification,
    DiscoverySprintRequest,
    SupportedRuleFamily,
)
from edgelab.intraday.historical_provider import HistoricalIntradayDataProvider
from edgelab.intraday.idea_batch_schema import (
    IDEA_BATCH_CODE_VERSION,
    AIProposedIntradayIdea,
    IdeaBatch,
    IdeaBatchDescription,
    IdeaBatchIdeaResult,
    IdeaBatchResult,
    IdeaBatchResultLabel,
    IdeaBatchRuleFamily,
    idea_batch_label,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIXTURE_IDEA_BATCH_DIR = _REPO_ROOT / "tests" / "fixtures" / "idea_batches"
DEFAULT_LOCAL_IDEA_BATCH_DIR = _REPO_ROOT / "data" / "processed" / "idea_batches"


@dataclass(frozen=True)
class IdeaBatchCacheKey:
    """Process-local cache key for idea batch results."""

    batch_id: str
    batch_hash: str
    file_signature: tuple[tuple[str, int, int], ...]
    code_version: str


_IDEA_BATCH_CACHE: dict[IdeaBatchCacheKey, IdeaBatchResult] = {}


class IdeaBatchRunner:
    """Load, validate, and test local structured idea batches."""

    def __init__(
        self,
        provider: HistoricalIntradayDataProvider | None = None,
        *,
        fixture_batch_dir: Path = DEFAULT_FIXTURE_IDEA_BATCH_DIR,
        local_batch_dir: Path = DEFAULT_LOCAL_IDEA_BATCH_DIR,
    ) -> None:
        self.provider = provider or FirstRateLocalCSVHistoricalProvider()
        self.fixture_batch_dir = fixture_batch_dir
        self.local_batch_dir = local_batch_dir
        self.discovery_sprint_service = DiscoverySprintService(self.provider)

    def list_batches(self) -> list[IdeaBatchDescription]:
        """Return lightweight descriptions without running historical tests."""

        return [self.describe_batch(batch.batch_id) for batch in self._load_batches()]

    def describe_batch(self, batch_id: str) -> IdeaBatchDescription:
        """Return validation-only metadata for one idea batch."""

        batch = self.load_batch(batch_id)
        accepted, rejected = self._validate_ideas(batch)
        unsupported = [
            self._unsupported_result(idea)
            for idea in accepted
            if not self._is_testable_rule(idea.supported_rule_family)
        ]
        securities = sorted(
            {
                symbol
                for idea in accepted
                if self._is_testable_rule(idea.supported_rule_family)
                for symbol in self._symbols_for_idea(idea)
            }
        )
        rejected_results = [*rejected, *unsupported]
        return IdeaBatchDescription(
            batch_id=batch.batch_id,
            batch_name=batch.batch_name,
            created_for=batch.created_for,
            ideas_submitted=len(batch.ideas),
            accepted_ideas=[
                idea.plain_english_name
                for idea in accepted
                if self._is_testable_rule(idea.supported_rule_family)
            ],
            rejected_ideas=[idea.plain_english_name for idea in rejected_results],
            securities_tested=securities,
            best_idea_if_any="Open the batch result to compute the local test.",
            current_conclusion="Not computed on the list page.",
            next_action="Open the local idea batch result.",
            evidence_details={
                "source": "checked-in demo fixture or ignored local batch file",
                "accepted_for_testing_count": sum(
                    self._is_testable_rule(idea.supported_rule_family) for idea in accepted
                ),
                "rejected_count": len(rejected_results),
            },
        )

    def load_batch(self, batch_id: str) -> IdeaBatch:
        """Load one local idea batch by ID."""

        for batch in self._load_batches():
            if batch.batch_id == batch_id:
                return batch
        raise KeyError(batch_id)

    def run_batch(self, batch_id: str) -> IdeaBatchResult:
        """Run one idea batch through local deterministic checks."""

        batch = self.load_batch(batch_id)
        return self.run_batch_payload(batch)

    def validate_batch_payload(self, payload: object) -> dict[str, Any]:
        """Validate one pasted idea batch without saving or running it."""

        batch = _payload_to_batch(payload)
        accepted_ideas, rejected_idea_results = self._validate_ideas(batch)
        unsupported_results = [
            self._unsupported_result(idea)
            for idea in accepted_ideas
            if not self._is_testable_rule(idea.supported_rule_family)
        ]
        testable_ideas = [
            idea for idea in accepted_ideas if self._is_testable_rule(idea.supported_rule_family)
        ]
        rejected_only = [
            result
            for result in rejected_idea_results
            if result.classification != IdeaBatchResultLabel.UNSUPPORTED_RULE
        ]
        unsupported_only = [
            result
            for result in [*rejected_idea_results, *unsupported_results]
            if result.classification == IdeaBatchResultLabel.UNSUPPORTED_RULE
        ]
        return {
            "batch_id": batch.batch_id,
            "batch_name": batch.batch_name,
            "created_for": batch.created_for,
            "ideas_submitted": len(batch.ideas),
            "accepted_ideas": [
                {
                    "idea_id": idea.idea_id,
                    "plain_english_name": idea.plain_english_name,
                    "supported_rule_family": idea.supported_rule_family.value,
                    "instruments_to_test": list(self._symbols_for_idea(idea)),
                }
                for idea in testable_ideas
            ],
            "rejected_ideas": [result.model_dump(mode="json") for result in rejected_only],
            "unsupported_ideas": [result.model_dump(mode="json") for result in unsupported_only],
            "safety_errors": [
                result.rejection_reason
                for result in rejected_only
                if result.rejection_reason is not None
            ],
            "can_run": bool(testable_ideas),
            "validation_status": (
                "Ready to run supported local ideas."
                if testable_ideas
                else "No supported local ideas are ready to run."
            ),
            "this_run_is_temporary": True,
            "research_only_status": "Research only",
            "real_money_status": "Not allowed",
            "does_not_call_ai": True,
            "does_not_save_results": True,
        }

    def run_batch_payload(self, payload: object) -> IdeaBatchResult:
        """Run one pasted idea batch without saving it."""

        batch = _payload_to_batch(payload)
        cache_key = self._cache_key(batch)
        cached = _IDEA_BATCH_CACHE.get(cache_key)
        if cached is not None:
            return cached.model_copy(
                update={
                    "cache_metadata": {
                        **cached.cache_metadata,
                        "cache_status": "cached",
                    }
                }
            )

        accepted_ideas, rejected_idea_results = self._validate_ideas(batch)
        accepted_results = [
            self._run_accepted_idea(idea)
            for idea in accepted_ideas
            if self._is_testable_rule(idea.supported_rule_family)
        ]
        unsupported_results = [
            self._unsupported_result(idea)
            for idea in accepted_ideas
            if not self._is_testable_rule(idea.supported_rule_family)
        ]
        tested_results = accepted_results
        all_rejected = [*rejected_idea_results, *unsupported_results]
        ranked = sorted(
            tested_results,
            key=lambda item: item.evidence_score,
            reverse=True,
        )
        worth_testing = [
            result
            for result in ranked
            if result.classification == IdeaBatchResultLabel.WORTH_TESTING_ON_MORE_HISTORY
        ]
        batch_result = IdeaBatchResult(
            batch_id=batch.batch_id,
            batch_name=batch.batch_name,
            created_for=batch.created_for,
            ideas_submitted=len(batch.ideas),
            ideas_tested=len(tested_results),
            securities_tested=sorted(
                {symbol for result in tested_results for symbol in result.securities_tested}
            ),
            best_idea_if_any=(
                worth_testing[0].plain_english_name if worth_testing else "No strong idea yet."
            ),
            current_conclusion=(
                f"{worth_testing[0].plain_english_name} is worth deeper local testing."
                if worth_testing
                else "No idea in this batch clearly earned more history yet."
            ),
            next_action=(
                "Review the top local idea before considering more history."
                if worth_testing
                else "Keep testing simple fixed ideas locally before buying more history."
            ),
            accepted_ideas=tested_results,
            rejected_ideas=all_rejected,
            ideas_needing_more_examples=[
                result.plain_english_name
                for result in tested_results
                if result.classification == IdeaBatchResultLabel.NEEDS_MORE_EXAMPLES
            ],
            ideas_mixed_results=[
                result.plain_english_name
                for result in tested_results
                if result.classification == IdeaBatchResultLabel.MIXED_RESULTS_NO_CLEAR_ANSWER
            ],
            ideas_rejected_for_now=[
                result.plain_english_name
                for result in [*tested_results, *all_rejected]
                if result.classification
                in {
                    IdeaBatchResultLabel.REJECT_FOR_NOW,
                    IdeaBatchResultLabel.UNSUPPORTED_RULE,
                    IdeaBatchResultLabel.DATA_PROBLEM,
                }
            ],
            ranked_results=ranked,
            cache_metadata={
                "cache_status": "computed",
                "code_version": IDEA_BATCH_CODE_VERSION,
            },
            evidence_details={
                "file_signature": [list(item) for item in cache_key.file_signature],
                "provider_data_quality_by_symbol": _provider_data_quality_by_symbol(self.provider),
                "data_quality_by_symbol": _data_quality_by_symbol_from_ranked(ranked),
                "unsupported_ideas": [
                    result.plain_english_name
                    for result in all_rejected
                    if result.classification == IdeaBatchResultLabel.UNSUPPORTED_RULE
                ],
                "unsafe_or_rejected_ideas": [
                    result.plain_english_name
                    for result in all_rejected
                    if result.classification == IdeaBatchResultLabel.REJECT_FOR_NOW
                ],
            },
        )
        _IDEA_BATCH_CACHE[cache_key] = batch_result
        return batch_result

    def _validate_ideas(
        self,
        batch: IdeaBatch,
    ) -> tuple[list[AIProposedIntradayIdea], list[IdeaBatchIdeaResult]]:
        accepted: list[AIProposedIntradayIdea] = []
        rejected: list[IdeaBatchIdeaResult] = []
        for raw_idea in batch.ideas:
            try:
                idea = AIProposedIntradayIdea.model_validate(raw_idea)
            except ValidationError as exc:
                rejected.append(_validation_rejection(raw_idea, exc))
                continue
            accepted.append(idea)
        return accepted, rejected

    def _run_accepted_idea(self, idea: AIProposedIntradayIdea) -> IdeaBatchIdeaResult:
        strategy_id = _strategy_for_idea(idea)
        request = DiscoverySprintRequest(symbols=self._symbols_for_idea(idea))
        strategy_result = self.discovery_sprint_service.strategy_result(
            strategy_id.value,
            request,
        )
        if strategy_result is None:
            return _rejected_result(
                idea_id=idea.idea_id,
                plain_english_name=idea.plain_english_name,
                supported_rule_family=idea.supported_rule_family.value,
                classification=IdeaBatchResultLabel.DATA_PROBLEM,
                reason="EdgeLab could not run this local deterministic rule.",
            )
        classification = _classification_from_discovery(strategy_result.classification)
        return IdeaBatchIdeaResult(
            idea_id=idea.idea_id,
            plain_english_name=idea.plain_english_name,
            supported_rule_family=idea.supported_rule_family.value,
            accepted_for_testing=True,
            classification=classification,
            classification_label=idea_batch_label(classification),
            securities_tested=[
                instrument.symbol for instrument in strategy_result.instrument_results
            ],
            current_conclusion=idea_batch_label(classification),
            next_action=_next_action_for_classification(classification),
            evidence_score=strategy_result.evidence_score,
            evidence_details={
                "source_strategy_id": strategy_result.strategy_id.value,
                "source_strategy_name": strategy_result.strategy_name,
                "source_conclusion": strategy_result.current_conclusion,
                "source_status": strategy_result.status,
                "source_next_action": strategy_result.next_research_action,
                "instrument_results": [
                    instrument.model_dump(mode="json")
                    for instrument in strategy_result.instrument_results
                ],
            },
        )

    def _unsupported_result(self, idea: AIProposedIntradayIdea) -> IdeaBatchIdeaResult:
        return _rejected_result(
            idea_id=idea.idea_id,
            plain_english_name=idea.plain_english_name,
            supported_rule_family=idea.supported_rule_family.value,
            classification=IdeaBatchResultLabel.UNSUPPORTED_RULE,
            reason="EdgeLab does not have a deterministic local test for this rule family yet.",
        )

    def _symbols_for_idea(self, idea: AIProposedIntradayIdea) -> tuple[str, ...]:
        available = set(self.provider.list_symbols())
        requested = tuple(symbol for symbol in idea.instruments_to_test if symbol in available)
        if idea.supported_rule_family == IdeaBatchRuleFamily.SYMBOL_DIVERGENCE:
            requested = tuple(symbol for symbol in ("QQQ", "SPY") if symbol in requested)
        return requested or idea.instruments_to_test

    def _is_testable_rule(self, rule: IdeaBatchRuleFamily) -> bool:
        return rule in _TESTABLE_RULES

    def _cache_key(self, batch: IdeaBatch) -> IdeaBatchCacheKey:
        return IdeaBatchCacheKey(
            batch_id=batch.batch_id,
            batch_hash=_batch_hash(batch),
            file_signature=_file_signature(self.provider),
            code_version=IDEA_BATCH_CODE_VERSION,
        )

    def _load_batches(self) -> list[IdeaBatch]:
        batches: dict[str, IdeaBatch] = {}
        for directory in (self.fixture_batch_dir, self.local_batch_dir):
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.json")):
                batch = IdeaBatch.model_validate_json(path.read_text(encoding="utf-8"))
                batches[batch.batch_id] = batch
        return list(batches.values())


_TESTABLE_RULES = {
    IdeaBatchRuleFamily.FIRST_RANGE_BREAKOUT,
    IdeaBatchRuleFamily.FIRST_RANGE_FAILURE,
    IdeaBatchRuleFamily.GAP_FADE,
    IdeaBatchRuleFamily.GAP_CONTINUATION,
    IdeaBatchRuleFamily.RECLAIM,
    IdeaBatchRuleFamily.TREND_CONTINUATION,
    IdeaBatchRuleFamily.SYMBOL_DIVERGENCE,
}


def _strategy_for_idea(idea: AIProposedIntradayIdea) -> SupportedRuleFamily:
    if idea.supported_rule_family == IdeaBatchRuleFamily.FIRST_RANGE_BREAKOUT:
        range_minutes = int(idea.fixed_parameters.get("range_minutes", 15))
        if range_minutes >= 30:
            return SupportedRuleFamily.FIRST_30_MINUTE_BREAKOUT
        return SupportedRuleFamily.FIRST_15_MINUTE_BREAKOUT
    if idea.supported_rule_family == IdeaBatchRuleFamily.FIRST_RANGE_FAILURE:
        return SupportedRuleFamily.FAILED_EARLY_MOVE
    if idea.supported_rule_family == IdeaBatchRuleFamily.GAP_FADE:
        return SupportedRuleFamily.GAP_FADE
    if idea.supported_rule_family == IdeaBatchRuleFamily.GAP_CONTINUATION:
        return SupportedRuleFamily.GAP_CONTINUATION
    if idea.supported_rule_family == IdeaBatchRuleFamily.RECLAIM:
        return SupportedRuleFamily.OPENING_RANGE_RECLAIM
    if idea.supported_rule_family == IdeaBatchRuleFamily.TREND_CONTINUATION:
        return SupportedRuleFamily.FIRST_15_MINUTE_BREAKOUT
    if idea.supported_rule_family == IdeaBatchRuleFamily.SYMBOL_DIVERGENCE:
        return SupportedRuleFamily.SPY_QQQ_DIVERGENCE
    raise ValueError(f"unsupported rule family: {idea.supported_rule_family}")


def _classification_from_discovery(
    classification: DiscoverySprintClassification,
) -> IdeaBatchResultLabel:
    if classification in {
        DiscoverySprintClassification.WORTH_MORE_TESTING,
        DiscoverySprintClassification.HELD_UP_ON_LATER_CHECK,
    }:
        return IdeaBatchResultLabel.WORTH_TESTING_ON_MORE_HISTORY
    if classification == DiscoverySprintClassification.NOT_ENOUGH_EXAMPLES:
        return IdeaBatchResultLabel.NEEDS_MORE_EXAMPLES
    if classification == DiscoverySprintClassification.DATA_PROBLEM:
        return IdeaBatchResultLabel.DATA_PROBLEM
    if classification == DiscoverySprintClassification.REJECT_FOR_NOW:
        return IdeaBatchResultLabel.REJECT_FOR_NOW
    return IdeaBatchResultLabel.MIXED_RESULTS_NO_CLEAR_ANSWER


def _next_action_for_classification(classification: IdeaBatchResultLabel) -> str:
    if classification == IdeaBatchResultLabel.WORTH_TESTING_ON_MORE_HISTORY:
        return "Consider more local history after reviewing the evidence details."
    if classification == IdeaBatchResultLabel.NEEDS_MORE_EXAMPLES:
        return "Get more local examples before judging this idea."
    if classification == IdeaBatchResultLabel.DATA_PROBLEM:
        return "Review local data quality before rerunning this idea."
    if classification == IdeaBatchResultLabel.UNSUPPORTED_RULE:
        return "Reject this idea until EdgeLab has a matching deterministic rule."
    if classification == IdeaBatchResultLabel.REJECT_FOR_NOW:
        return "Reject for now and focus on other local ideas."
    return "Keep it on the research board, but do not advance it yet."


def _validation_rejection(raw_idea: dict[str, Any], exc: ValidationError) -> IdeaBatchIdeaResult:
    missing_fields = [
        str(error.get("loc", ("field",))[-1])
        for error in exc.errors()
        if error.get("type") == "missing"
    ]
    classification = (
        IdeaBatchResultLabel.UNSUPPORTED_RULE
        if any("supported_rule_family" in str(error.get("loc", ())) for error in exc.errors())
        else IdeaBatchResultLabel.REJECT_FOR_NOW
    )
    reason = _validation_rejection_reason(
        exc,
        classification=classification,
        missing_fields=missing_fields,
    )
    return _rejected_result(
        idea_id=_safe_raw_value(raw_idea.get("idea_id"), "rejected_idea"),
        plain_english_name=_safe_raw_value(raw_idea.get("idea_id"), "Rejected idea"),
        supported_rule_family=str(raw_idea.get("supported_rule_family", "unknown")),
        classification=classification,
        reason=reason,
    )


def _validation_rejection_reason(
    exc: ValidationError,
    *,
    classification: IdeaBatchResultLabel,
    missing_fields: list[str],
) -> str:
    if missing_fields:
        return f"Missing required field: {', '.join(missing_fields)}."
    messages = " ".join(str(error.get("msg", "")) for error in exc.errors()).lower()
    if classification == IdeaBatchResultLabel.UNSUPPORTED_RULE:
        return "Unsupported rule family: EdgeLab cannot test this idea with current local rules."
    if "action instructions" in messages:
        return "Unsafe language found: buy/sell/short instruction."
    if "unsafe research language" in messages:
        return "Unsafe language found: proof, readiness, or result claim."
    return "EdgeLab rejected this idea because its wording was unsafe for research output."


def _payload_to_batch(payload: object) -> IdeaBatch:
    if isinstance(payload, IdeaBatch):
        return payload
    if not isinstance(payload, dict):
        raise ValueError("Invalid JSON: the batch must be a JSON object.")
    return IdeaBatch.model_validate(payload)


def _rejected_result(
    *,
    idea_id: str,
    plain_english_name: str,
    supported_rule_family: str,
    classification: IdeaBatchResultLabel,
    reason: str,
) -> IdeaBatchIdeaResult:
    return IdeaBatchIdeaResult(
        idea_id=idea_id,
        plain_english_name=plain_english_name,
        supported_rule_family=supported_rule_family,
        accepted_for_testing=False,
        classification=classification,
        classification_label=idea_batch_label(classification),
        securities_tested=[],
        current_conclusion=idea_batch_label(classification),
        next_action=_next_action_for_classification(classification),
        rejection_reason=reason,
        evidence_details={"rejection_reason": reason},
    )


def _safe_raw_value(value: object, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,80}", value):
        return value
    return fallback


def _batch_hash(batch: IdeaBatch) -> str:
    payload = json.dumps(batch.model_dump(mode="json"), sort_keys=True)
    return sha256(payload.encode("utf-8")).hexdigest()


def _file_signature(
    provider: HistoricalIntradayDataProvider,
) -> tuple[tuple[str, int, int], ...]:
    if isinstance(provider, FirstRateLocalCSVHistoricalProvider):
        return tuple(
            sorted(
                (item.path, item.size_bytes, item.modified_time_ns)
                for item in provider.file_cache_signature()
            )
        )
    return ()


def _provider_data_quality_by_symbol(
    provider: HistoricalIntradayDataProvider,
) -> list[dict[str, Any]]:
    if not isinstance(provider, FirstRateLocalCSVHistoricalProvider):
        return []
    dry_run = provider.dry_run()
    return [
        {
            "symbol": summary.symbol,
            "sessions": summary.session_count,
            "ready_sessions": int(summary.readiness_counts.get("ready_for_replay", 0)),
            "quality_issues": summary.quality_issue_count,
        }
        for summary in dry_run.files
    ]


def _data_quality_by_symbol_from_ranked(
    ranked: list[IdeaBatchIdeaResult],
) -> list[dict[str, Any]]:
    for result in ranked:
        source = result.evidence_details.get("instrument_results")
        if isinstance(source, list):
            return [
                {
                    "symbol": item.get("symbol"),
                    "sessions_tested": item.get("sessions_tested"),
                    "usable_sessions": item.get("usable_sessions"),
                    "data_warnings": item.get("data_warnings", []),
                }
                for item in source
                if isinstance(item, dict)
            ]
    return []
