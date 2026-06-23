"""Deterministic local runner for structured intraday idea batches."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
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
    IdeaBatchSymbolResultSummary,
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
            "validation_errors": [
                result.rejection_reason
                for result in rejected_only
                if result.rejection_reason is not None
            ],
            "can_run": bool(testable_ideas),
            "validation_status": (
                "Supported local ideas can run."
                if testable_ideas
                else "No supported local ideas can run yet."
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
        batch_evidence = _batch_evidence_details(ranked, all_rejected)
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
                **batch_evidence,
                "file_signature": [list(item) for item in cache_key.file_signature],
                "provider_data_quality_by_symbol": _provider_data_quality_by_symbol(self.provider),
                "data_quality_by_symbol": _data_quality_by_symbol_from_ranked(ranked),
                "unsupported_ideas": [
                    result.plain_english_name
                    for result in all_rejected
                    if result.classification == IdeaBatchResultLabel.UNSUPPORTED_RULE
                ],
                "rejected_ideas": [
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
        evidence = _idea_evidence_details(
            idea=idea,
            classification=classification,
            instrument_results=strategy_result.instrument_results,
        )
        return IdeaBatchIdeaResult(
            idea_id=idea.idea_id,
            plain_english_name=idea.plain_english_name,
            supported_rule_family=idea.supported_rule_family.value,
            accepted_for_testing=True,
            classification=classification,
            classification_label=idea_batch_label(classification),
            outcome_label=idea_batch_label(classification),
            securities_tested=[
                instrument.symbol for instrument in strategy_result.instrument_results
            ],
            symbols_tested=[instrument.symbol for instrument in strategy_result.instrument_results],
            current_conclusion=idea_batch_label(classification),
            next_action=_next_action_for_classification(classification),
            example_count_total=evidence["example_count_total"],
            example_count_by_symbol=evidence["example_count_by_symbol"],
            symbol_result_summary=evidence["symbol_result_summary"],
            best_symbol=evidence["best_symbol"],
            worst_symbol=evidence["worst_symbol"],
            closest_to_interesting_reason=evidence["closest_to_interesting_reason"],
            why_label_was_assigned=evidence["why_label_was_assigned"],
            what_to_try_next=evidence["what_to_try_next"],
            result_confidence_explanation=evidence["result_confidence_explanation"],
            evidence_score=strategy_result.evidence_score,
            evidence_details={
                "source_strategy_id": strategy_result.strategy_id.value,
                "source_strategy_name": strategy_result.strategy_name,
                "source_conclusion": strategy_result.current_conclusion,
                "source_status": strategy_result.status,
                "source_next_action": strategy_result.next_research_action,
                "example_count_total": evidence["example_count_total"],
                "example_count_by_symbol": evidence["example_count_by_symbol"],
                "symbol_result_summary": [
                    item.model_dump(mode="json") for item in evidence["symbol_result_summary"]
                ],
                "best_symbol": evidence["best_symbol"],
                "worst_symbol": evidence["worst_symbol"],
                "closest_to_interesting_reason": evidence["closest_to_interesting_reason"],
                "why_label_was_assigned": evidence["why_label_was_assigned"],
                "what_to_try_next": evidence["what_to_try_next"],
                "result_confidence_explanation": evidence["result_confidence_explanation"],
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
        return requested or tuple(idea.instruments_to_test)

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
    idea_id = _safe_raw_value(raw_idea.get("idea_id"), "rejected_idea")
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
        idea_id=idea_id,
        classification=classification,
        missing_fields=missing_fields,
    )
    return _rejected_result(
        idea_id=idea_id,
        plain_english_name=_safe_raw_value(raw_idea.get("plain_english_name"), idea_id),
        supported_rule_family=str(raw_idea.get("supported_rule_family", "unknown")),
        classification=classification,
        reason=reason,
    )


def _validation_rejection_reason(
    exc: ValidationError,
    *,
    idea_id: str,
    classification: IdeaBatchResultLabel,
    missing_fields: list[str],
) -> str:
    if missing_fields:
        return f"{idea_id}: missing required field: {', '.join(missing_fields)}."
    if classification == IdeaBatchResultLabel.UNSUPPORTED_RULE:
        return "Unsupported rule family: EdgeLab cannot test this idea with current local rules."
    return " ".join(_validation_error_message(idea_id, error) for error in exc.errors())


def _validation_error_message(idea_id: str, error: Mapping[str, Any]) -> str:
    loc = ".".join(str(part) for part in error.get("loc", ())) or "idea"
    error_type = str(error.get("type", ""))
    if error_type == "list_type":
        return f"{idea_id}: {loc} must be a list of strings."
    if error_type == "dict_type":
        return f"{idea_id}: {loc} must be an object."
    if error_type == "string_type":
        return f"{idea_id}: {loc} must be a string."
    if error_type in {"int_type", "float_type", "bool_type"}:
        return f"{idea_id}: {loc} has the wrong JSON value type."
    if error_type == "too_short":
        return f"{idea_id}: {loc} must not be empty."
    message = str(error.get("msg", "Invalid value"))
    return f"{idea_id}: {loc}: {message}."


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
    evidence = _not_tested_evidence(
        classification=classification,
        reason=reason,
    )
    return IdeaBatchIdeaResult(
        idea_id=idea_id,
        plain_english_name=plain_english_name,
        supported_rule_family=supported_rule_family,
        accepted_for_testing=False,
        classification=classification,
        classification_label=idea_batch_label(classification),
        outcome_label=idea_batch_label(classification),
        securities_tested=[],
        symbols_tested=[],
        current_conclusion=idea_batch_label(classification),
        next_action=_next_action_for_classification(classification),
        rejection_reason=reason,
        example_count_total=0,
        example_count_by_symbol={},
        symbol_result_summary=[],
        best_symbol=None,
        worst_symbol=None,
        closest_to_interesting_reason=evidence["closest_to_interesting_reason"],
        why_label_was_assigned=evidence["why_label_was_assigned"],
        what_to_try_next=evidence["what_to_try_next"],
        result_confidence_explanation=evidence["result_confidence_explanation"],
        evidence_details={
            "not_tested": True,
            "rejection_reason": reason,
            **evidence,
        },
    )


def _idea_evidence_details(
    *,
    idea: AIProposedIntradayIdea,
    classification: IdeaBatchResultLabel,
    instrument_results: list[Any],
) -> dict[str, Any]:
    summaries = [_symbol_result_summary(result) for result in instrument_results]
    example_count_by_symbol = {
        str(result.symbol): int(result.examples_found) for result in instrument_results
    }
    best_symbol = _best_symbol(instrument_results)
    worst_symbol = _worst_symbol(instrument_results)
    return {
        "example_count_total": sum(example_count_by_symbol.values()),
        "example_count_by_symbol": example_count_by_symbol,
        "symbol_result_summary": summaries,
        "best_symbol": best_symbol,
        "worst_symbol": worst_symbol,
        "closest_to_interesting_reason": _closest_to_interesting_reason(
            idea=idea,
            classification=classification,
            instrument_results=instrument_results,
            best_symbol=best_symbol,
            worst_symbol=worst_symbol,
        ),
        "why_label_was_assigned": _why_label_was_assigned(
            classification,
            instrument_results,
        ),
        "what_to_try_next": _what_to_try_next(
            classification=classification,
            idea=idea,
            instrument_results=instrument_results,
            best_symbol=best_symbol,
        ),
        "result_confidence_explanation": _result_confidence_explanation(
            classification,
            instrument_results,
        ),
    }


def _symbol_result_summary(result: Any) -> IdeaBatchSymbolResultSummary:
    label = _simple_symbol_result_label(result)
    return IdeaBatchSymbolResultSummary(
        symbol=str(result.symbol),
        matched_examples=int(result.examples_found),
        simple_result_label=label,
        plain_english_reason=_symbol_plain_reason(result, label),
    )


def _simple_symbol_result_label(result: Any) -> str:
    classification = result.classification
    completed = int(result.completed_examples)
    if classification == DiscoverySprintClassification.DATA_PROBLEM:
        return "Data problem"
    if completed == 0 and result.data_warnings:
        return "Data problem"
    if classification == DiscoverySprintClassification.NOT_ENOUGH_EXAMPLES or completed < 10:
        return "Too few examples"
    if classification in {
        DiscoverySprintClassification.WORTH_MORE_TESTING,
        DiscoverySprintClassification.HELD_UP_ON_LATER_CHECK,
        DiscoverySprintClassification.LOOKED_BETTER_AT_FIRST,
    }:
        return "Helpful"
    if classification == DiscoverySprintClassification.REJECT_FOR_NOW:
        return "Unhelpful"
    share = _instrument_helpful_share(result)
    if share is not None and share >= 0.58:
        return "Helpful"
    if share is not None and share <= 0.40:
        return "Unhelpful"
    return "Mixed results / no clear answer"


def _symbol_plain_reason(result: Any, label: str) -> str:
    symbol = str(result.symbol)
    completed = int(result.completed_examples)
    if label == "Data problem":
        return f"{symbol} had a local data problem, so EdgeLab could not read this symbol fairly."
    if label == "Too few examples":
        return f"{symbol} had {completed} completed examples, which is too few for a fair read."
    expected = int(result.moved_as_expected_count)
    against = int(result.moved_against_test_count)
    flat = int(result.did_not_move_enough_count)
    if label == "Helpful":
        return (
            f"This symbol helped: {expected} of {completed} completed examples moved as "
            f"the idea expected."
        )
    if label == "Unhelpful":
        return (
            f"This symbol hurt: {against} of {completed} completed examples moved against "
            f"the idea, and {flat} did not move enough to matter."
        )
    return (
        f"{symbol} was split: {expected} moved as expected, {against} moved against "
        f"the idea, and {flat} did not move enough to matter."
    )


def _best_symbol(instrument_results: list[Any]) -> str | None:
    candidates = [
        result
        for result in instrument_results
        if int(result.completed_examples) > 0
        and _simple_symbol_result_label(result) not in {"Data problem", "Too few examples"}
    ]
    if not candidates:
        return None
    return str(
        max(
            candidates,
            key=lambda result: (
                _instrument_helpful_share(result) or 0.0,
                int(result.completed_examples),
            ),
        ).symbol
    )


def _worst_symbol(instrument_results: list[Any]) -> str | None:
    candidates = [
        result
        for result in instrument_results
        if int(result.completed_examples) > 0
        and _simple_symbol_result_label(result) not in {"Data problem", "Too few examples"}
    ]
    if not candidates:
        return None
    return str(
        min(
            candidates,
            key=lambda result: (
                _instrument_helpful_share(result)
                if _instrument_helpful_share(result) is not None
                else 1.0,
                -int(result.completed_examples),
            ),
        ).symbol
    )


def _closest_to_interesting_reason(
    *,
    idea: AIProposedIntradayIdea,
    classification: IdeaBatchResultLabel,
    instrument_results: list[Any],
    best_symbol: str | None,
    worst_symbol: str | None,
) -> str:
    if not instrument_results:
        return "EdgeLab could not test this idea with the local data available."
    counts = _symbol_label_counts(instrument_results)
    if classification == IdeaBatchResultLabel.NEEDS_MORE_EXAMPLES:
        return "This needs more history because the local sample did not find enough examples."
    if classification == IdeaBatchResultLabel.REJECT_FOR_NOW:
        if counts["Unhelpful"] > 1:
            return "This was rejected because several tested symbols hurt the idea."
        return (
            "This was rejected because the tested symbols did not separate better mornings "
            "from worse mornings."
        )
    if classification == IdeaBatchResultLabel.WORTH_TESTING_ON_MORE_HISTORY:
        if best_symbol is not None:
            return (
                f"{best_symbol} looked closest to helpful, but EdgeLab still needs a tighter "
                "follow-up before trusting the idea."
            )
        return "One pocket looked closest to helpful, but EdgeLab still needs a tighter follow-up."
    if best_symbol and worst_symbol and best_symbol != worst_symbol:
        return f"{best_symbol} looked closest to helpful, but {worst_symbol} did not confirm it."
    if counts["Helpful"] > 0 and counts["Unhelpful"] > 0:
        return "Some symbols helped and others hurt, so the idea did not give one clear answer."
    if idea.supported_rule_family == IdeaBatchRuleFamily.SYMBOL_DIVERGENCE:
        return "The pair check did not show a clean enough difference between the symbols."
    return "The idea found examples, but the results were split across symbols."


def _why_label_was_assigned(
    classification: IdeaBatchResultLabel,
    instrument_results: list[Any],
) -> str:
    counts = _symbol_label_counts(instrument_results)
    total_examples = sum(int(result.examples_found) for result in instrument_results)
    if classification == IdeaBatchResultLabel.NEEDS_MORE_EXAMPLES:
        return (
            f"This was marked Too few examples because EdgeLab found {total_examples} "
            "matching mornings across the tested symbols."
        )
    if classification == IdeaBatchResultLabel.REJECT_FOR_NOW:
        return (
            "This was marked Reject for now because the tested symbols mostly moved against "
            "the idea or did not separate better mornings from worse mornings."
        )
    if classification == IdeaBatchResultLabel.DATA_PROBLEM:
        return "This was marked Local data problem because local data blocked a fair read."
    if classification == IdeaBatchResultLabel.WORTH_TESTING_ON_MORE_HISTORY:
        return (
            "This was marked Worth testing on more history because at least one tested symbol "
            "looked helpful in the local sample."
        )
    if counts["Helpful"] > 0 and counts["Unhelpful"] > 0:
        return (
            "This was marked Mixed results / no clear answer because some symbols looked "
            "helpful and others did not."
        )
    return (
        "This was marked Mixed results / no clear answer because EdgeLab found examples, "
        "but the result was not consistent enough across symbols."
    )


def _what_to_try_next(
    *,
    classification: IdeaBatchResultLabel,
    idea: AIProposedIntradayIdea,
    instrument_results: list[Any],
    best_symbol: str | None,
) -> str:
    if classification == IdeaBatchResultLabel.NEEDS_MORE_EXAMPLES:
        return "Do not judge this idea until more local history is available."
    if classification == IdeaBatchResultLabel.REJECT_FOR_NOW:
        return "Reject for now and avoid retesting the same broad idea unchanged."
    if classification == IdeaBatchResultLabel.DATA_PROBLEM:
        return "Review local data quality before testing this idea again."
    if best_symbol is not None:
        return f"Retest this narrower idea around {best_symbol} and require clearer confirmation."
    if idea.supported_rule_family == IdeaBatchRuleFamily.RECLAIM:
        return "Try a stricter reclaim version that requires more confirming symbols."
    if idea.supported_rule_family == IdeaBatchRuleFamily.FIRST_RANGE_FAILURE:
        return "Try this only after unusually wide early ranges."
    return "Try a narrower version with fewer symbols and clearer confirmation rules."


def _result_confidence_explanation(
    classification: IdeaBatchResultLabel,
    instrument_results: list[Any],
) -> str:
    counts = _symbol_label_counts(instrument_results)
    if classification == IdeaBatchResultLabel.NEEDS_MORE_EXAMPLES:
        return "Low confidence because there were too few examples."
    if classification == IdeaBatchResultLabel.REJECT_FOR_NOW and counts["Unhelpful"] > 1:
        return (
            "Moderate confidence for rejecting this locally because several symbols failed "
            "in the same way."
        )
    if counts["Helpful"] > 0 and counts["Unhelpful"] > 0:
        return "Low confidence because results differed across symbols."
    return "Low confidence because the local sample is limited and this is only a first read."


def _not_tested_evidence(
    *,
    classification: IdeaBatchResultLabel,
    reason: str,
) -> dict[str, str]:
    if classification == IdeaBatchResultLabel.UNSUPPORTED_RULE:
        return {
            "closest_to_interesting_reason": (
                "Not tested. EdgeLab does not currently have local rule logic for this idea shape."
            ),
            "why_label_was_assigned": f"Not tested because {reason}",
            "what_to_try_next": (
                "Rewrite this idea using one of the supported rule families, or add a new "
                "local rule in a future phase."
            ),
            "result_confidence_explanation": (
                "No result confidence because this idea was not tested."
            ),
        }
    return {
        "closest_to_interesting_reason": "Not tested because the idea batch entry needs changes.",
        "why_label_was_assigned": f"Not tested because {reason}",
        "what_to_try_next": "Fix the JSON structure, then validate the batch again.",
        "result_confidence_explanation": "No result confidence because this idea was not tested.",
    }


def _batch_evidence_details(
    ranked: list[IdeaBatchIdeaResult],
    rejected: list[IdeaBatchIdeaResult],
) -> dict[str, Any]:
    advanced = [
        result
        for result in ranked
        if result.classification == IdeaBatchResultLabel.WORTH_TESTING_ON_MORE_HISTORY
    ]
    mixed = [
        result
        for result in ranked
        if result.classification == IdeaBatchResultLabel.MIXED_RESULTS_NO_CLEAR_ANSWER
    ]
    rejected_or_blocked = [
        result
        for result in [*ranked, *rejected]
        if result.classification
        in {
            IdeaBatchResultLabel.REJECT_FOR_NOW,
            IdeaBatchResultLabel.UNSUPPORTED_RULE,
            IdeaBatchResultLabel.DATA_PROBLEM,
        }
    ]
    closest = advanced[0] if advanced else _closest_ranked_result(ranked)
    closest_name = closest.plain_english_name if closest is not None else "No clear candidate yet."
    closest_reason = (
        closest.closest_to_interesting_reason
        if closest is not None
        else "No tested idea was close enough to narrow yet."
    )
    return {
        "ideas_advanced_count": len(advanced),
        "ideas_rejected_count": len(rejected_or_blocked),
        "ideas_mixed_or_unclear_count": len(mixed),
        "closest_to_interesting_idea": closest_name,
        "closest_to_interesting_reason": closest_reason,
        "recommended_next_research_focus": _recommended_next_research_focus(closest),
        "batch_plain_english_summary": _batch_plain_summary(
            advanced_count=len(advanced),
            closest_name=closest_name,
            closest_reason=closest_reason,
        ),
    }


def _closest_ranked_result(ranked: list[IdeaBatchIdeaResult]) -> IdeaBatchIdeaResult | None:
    for result in ranked:
        if result.classification not in {
            IdeaBatchResultLabel.REJECT_FOR_NOW,
            IdeaBatchResultLabel.DATA_PROBLEM,
        }:
            return result
    return ranked[0] if ranked else None


def _recommended_next_research_focus(result: IdeaBatchIdeaResult | None) -> str:
    if result is None:
        return "Try a simpler idea family or add more local history before narrowing."
    if result.classification == IdeaBatchResultLabel.NEEDS_MORE_EXAMPLES:
        return "More local history before judging this idea family."
    if result.supported_rule_family == IdeaBatchRuleFamily.RECLAIM.value:
        return "Reclaim ideas with fewer symbols and clearer confirmation."
    if result.supported_rule_family == IdeaBatchRuleFamily.FIRST_RANGE_FAILURE.value:
        return "Failed early move ideas with stricter early-range conditions."
    if result.supported_rule_family == IdeaBatchRuleFamily.SYMBOL_DIVERGENCE.value:
        return "Symbol disagreement checks only if the pair evidence improves."
    return "A narrower version of the closest mixed idea."


def _batch_plain_summary(
    *,
    advanced_count: int,
    closest_name: str,
    closest_reason: str,
) -> str:
    if advanced_count == 0:
        return f"Nothing advanced. Closest to interesting: {closest_name}. {closest_reason}"
    return (
        f"{advanced_count} idea moved to deeper local research. Closest to interesting: "
        f"{closest_name}. {closest_reason}"
    )


def _symbol_label_counts(instrument_results: list[Any]) -> dict[str, int]:
    counts = {
        "Helpful": 0,
        "Unhelpful": 0,
        "Mixed results / no clear answer": 0,
        "Too few examples": 0,
        "Data problem": 0,
    }
    for result in instrument_results:
        counts[_simple_symbol_result_label(result)] += 1
    return counts


def _instrument_helpful_share(result: Any) -> float | None:
    completed = int(result.completed_examples)
    if completed <= 0:
        return None
    return int(result.moved_as_expected_count) / completed


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
