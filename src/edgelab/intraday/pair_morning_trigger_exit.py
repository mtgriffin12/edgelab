"""Generic local pair morning trigger/exit research study."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, time
from pathlib import Path
from statistics import mean, median
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from edgelab.intraday.spy_csgp_morning_divergence import (
    DEFAULT_CSGP_RECENT_PATH,
    DEFAULT_SPY_RECENT_PATH,
    DateRangeSummary,
    MorningDivergenceFileSummary,
    _date_range_summary,
    _load_symbol_bars,
    _LocalBar,
    _overlap_range_summary,
    _sample_description,
)

DEFAULT_TRIGGER_TIME = time(10, 0)
DEFAULT_MORNING_START = time(9, 30)
DEFAULT_OUTCOME_WINDOWS = [
    ("trigger_to_30_minutes", "10:00-10:30", time(10, 30)),
    ("trigger_to_60_minutes", "10:00-11:00", time(11, 0)),
    ("trigger_to_120_minutes", "10:00-12:00", time(12, 0)),
    ("trigger_to_close", "10:00-16:00", time(16, 0)),
]
EXIT_THRESHOLDS = [0.50, 1.00, 2.00, 3.00]


class PairMorningTriggerExitConfig(BaseModel):
    """Pair-flexible configuration for a local trigger/exit study."""

    study_name: str = Field(min_length=1)
    primary_symbol: str = Field(min_length=1)
    comparison_symbol: str = Field(min_length=1)
    primary_file_path: Path
    comparison_file_path: Path
    relationship_name: str = Field(min_length=1)
    primary_down_label: str = Field(min_length=1)
    primary_up_label: str = Field(min_length=1)
    comparison_stronger_label: str = Field(min_length=1)
    comparison_weaker_label: str = Field(min_length=1)
    trigger_time: time = DEFAULT_TRIGGER_TIME
    morning_windows: list[str] = Field(default_factory=lambda: ["9:30-10:00"])
    outcome_windows: list[str] = Field(
        default_factory=lambda: [label for _id, label, _end in DEFAULT_OUTCOME_WINDOWS]
    )
    primary_move_thresholds: list[float] = Field(default_factory=lambda: [0.50, 0.75, 1.00])
    comparison_move_thresholds: list[float] = Field(default_factory=lambda: [0.00, 0.50, 1.00])
    relative_spread_thresholds: list[float] = Field(default_factory=lambda: [1.00])


class TriggerConditionDefinition(BaseModel):
    """One trigger condition the pair engine can test."""

    condition_id: str = Field(min_length=1)
    family_id: str = Field(min_length=1)
    family_label: str = Field(min_length=1)
    trigger_label: str = Field(min_length=1)
    primary_direction: Literal["down", "up"]
    primary_threshold_pct: float
    comparison_rule: Literal["above_zero", "below_zero", "at_least", "at_most", "spread"]
    comparison_threshold_pct: float | None = None
    spread_threshold_pct: float | None = None
    favorable_direction: Literal["higher", "lower"]


class TriggerExample(BaseModel):
    """One date that matched a trigger and its post-trigger behavior."""

    date: date
    condition_id: str = Field(min_length=1)
    trigger_label: str = Field(min_length=1)
    family_label: str = Field(min_length=1)
    outcome_window: str = Field(min_length=1)
    primary_morning_move: float
    comparison_morning_move: float
    comparison_post_trigger_move: float
    max_favorable_move: float
    max_adverse_move: float
    gave_back_half: bool
    kept_half: bool
    plain_english_summary: str = Field(min_length=1)


class OutcomeWindowSummary(BaseModel):
    """Outcome result for one trigger condition and one post-trigger window."""

    condition_id: str = Field(min_length=1)
    trigger_label: str = Field(min_length=1)
    family_id: str = Field(min_length=1)
    family_label: str = Field(min_length=1)
    outcome_window_id: str = Field(min_length=1)
    outcome_window_label: str = Field(min_length=1)
    matching_mornings: int = Field(ge=0)
    average_post_trigger_move: float | None = None
    median_post_trigger_move: float | None = None
    favorable_count: int = Field(ge=0)
    favorable_percent: float | None = None
    adverse_count: int = Field(ge=0)
    adverse_percent: float | None = None
    best_date: date | None = None
    worst_date: date | None = None
    average_max_favorable_move: float | None = None
    average_max_adverse_move: float | None = None
    threshold_reached_counts: dict[str, int] = Field(default_factory=dict)
    gave_back_half_count: int = Field(ge=0)
    kept_half_count: int = Field(ge=0)
    sample_size_warning: str = Field(min_length=1)
    rating: str = Field(min_length=1)
    plain_english_summary: str = Field(min_length=1)


class TriggerConditionSummary(BaseModel):
    """Summary across outcome windows for one trigger condition."""

    condition_id: str = Field(min_length=1)
    trigger_label: str = Field(min_length=1)
    family_id: str = Field(min_length=1)
    family_label: str = Field(min_length=1)
    examples_found: int = Field(ge=0)
    best_outcome_window: str = Field(min_length=1)
    best_rating: str = Field(min_length=1)
    plain_english_summary: str = Field(min_length=1)


class SetupFamilySummary(BaseModel):
    """One side of the pair relationship being tested."""

    family_id: str = Field(min_length=1)
    family_label: str = Field(min_length=1)
    trigger_time_label: str = Field(min_length=1)
    trigger_conditions: list[TriggerConditionSummary] = Field(default_factory=list)
    plain_english_summary: str = Field(min_length=1)


class RankedTriggerExitCombination(BaseModel):
    """Conservative ranking for one trigger plus one post-trigger window."""

    rank: int = Field(ge=1)
    condition_id: str = Field(min_length=1)
    trigger_label: str = Field(min_length=1)
    outcome_window_label: str = Field(min_length=1)
    examples_found: int = Field(ge=0)
    favorable_percent: float | None = None
    median_post_trigger_move: float | None = None
    average_max_favorable_move: float | None = None
    average_max_adverse_move: float | None = None
    sample_size_warning: str = Field(min_length=1)
    rating: str = Field(min_length=1)
    plain_english_summary: str = Field(min_length=1)


class PairMorningTriggerExitStudy(BaseModel):
    """Read-only result for a generic pair trigger/exit study."""

    study_id: str = "phase-7x-2v-pair-trigger-exit-study"
    study_name: str = Field(min_length=1)
    primary_symbol: str = Field(min_length=1)
    comparison_symbol: str = Field(min_length=1)
    primary_file_used: str = Field(min_length=1)
    comparison_file_used: str = Field(min_length=1)
    relationship_tested: str = Field(min_length=1)
    data_readiness_summary: str = Field(min_length=1)
    files_used: list[MorningDivergenceFileSummary] = Field(min_length=1)
    primary_file_range: DateRangeSummary
    comparison_file_range: DateRangeSummary
    overlap_range_analyzed: DateRangeSummary
    overlapping_start_date: date | None = None
    overlapping_end_date: date | None = None
    trading_days_analyzed: int = Field(ge=0)
    sample_description: str = Field(min_length=1)
    trigger_time_label: str = Field(min_length=1)
    morning_windows_tested: list[str] = Field(default_factory=list)
    outcome_windows_tested: list[str] = Field(default_factory=list)
    setup_families: list[SetupFamilySummary] = Field(default_factory=list)
    trigger_condition_summaries: list[TriggerConditionSummary] = Field(default_factory=list)
    outcome_window_summaries: list[OutcomeWindowSummary] = Field(default_factory=list)
    ranked_trigger_exit_combinations: list[RankedTriggerExitCombination] = Field(
        default_factory=list
    )
    strongest_examples: list[TriggerExample] = Field(default_factory=list)
    weakest_examples: list[TriggerExample] = Field(default_factory=list)
    giveback_hold_summary: str = Field(min_length=1)
    best_current_research_clue: str = Field(min_length=1)
    examples_are_too_few: bool
    plain_english_bottom_line: str = Field(min_length=1)
    what_to_study_next: list[str] = Field(default_factory=list)
    no_external_calls: bool = True
    no_live_data: bool = True
    no_saved_outputs: bool = True
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"

    @model_validator(mode="after")
    def validate_safety(self) -> Self:
        """Keep the study local and research-only."""

        if not self.no_external_calls:
            raise ValueError("Pair trigger/exit study must not call external services")
        if not self.no_live_data:
            raise ValueError("Pair trigger/exit study must not use live data")
        if not self.no_saved_outputs:
            raise ValueError("Pair trigger/exit study must not save outputs")
        if self.research_only_status != "Research only":
            raise ValueError("Pair trigger/exit study must remain research-only")
        if self.real_money_status != "Not allowed":
            raise ValueError("Pair trigger/exit study real-money status must be Not allowed")
        return self


class PairMorningTriggerExitStudyService:
    """Run a configured local pair trigger/exit study."""

    def __init__(self, config: PairMorningTriggerExitConfig) -> None:
        self.config = config

    def run(self) -> PairMorningTriggerExitStudy:
        """Read configured local files and compute trigger/exit results."""

        config = self.config
        primary_file, primary_bars = _load_symbol_bars(
            config.primary_symbol, config.primary_file_path
        )
        comparison_file, comparison_bars = _load_symbol_bars(
            config.comparison_symbol, config.comparison_file_path
        )
        common_dates = sorted(set(primary_bars) & set(comparison_bars))
        definitions = _trigger_definitions(config)
        examples_by_condition = {
            definition.condition_id: _matching_trigger_dates(
                definition, primary_bars, comparison_bars, common_dates, config
            )
            for definition in definitions
        }
        outcome_summaries: list[OutcomeWindowSummary] = []
        all_examples: list[TriggerExample] = []
        for definition in definitions:
            for outcome_id, outcome_label, outcome_end in DEFAULT_OUTCOME_WINDOWS:
                summary, examples = _outcome_summary(
                    definition=definition,
                    trigger_examples=examples_by_condition[definition.condition_id],
                    primary_bars=primary_bars,
                    comparison_bars=comparison_bars,
                    outcome_window_id=outcome_id,
                    outcome_window_label=outcome_label,
                    outcome_end=outcome_end,
                    config=config,
                )
                outcome_summaries.append(summary)
                all_examples.extend(examples)
        condition_summaries = _condition_summaries(definitions, outcome_summaries)
        families = _family_summaries(config, condition_summaries)
        ranked = _rank_outcomes(outcome_summaries)
        strongest, weakest = _strongest_and_weakest_examples(all_examples)
        giveback_hold_summary = _giveback_hold_summary(outcome_summaries)
        best_clue = _best_current_research_clue(ranked)
        bottom_line = _bottom_line(
            ranked, len(common_dates), _sample_description(len(common_dates))
        )
        return PairMorningTriggerExitStudy(
            study_name=config.study_name,
            primary_symbol=config.primary_symbol,
            comparison_symbol=config.comparison_symbol,
            primary_file_used=str(config.primary_file_path),
            comparison_file_used=str(config.comparison_file_path),
            relationship_tested=config.relationship_name,
            data_readiness_summary=_data_readiness_summary(
                primary_file, comparison_file, common_dates
            ),
            files_used=[primary_file, comparison_file],
            primary_file_range=_date_range_summary(f"{config.primary_symbol} file", primary_file),
            comparison_file_range=_date_range_summary(
                f"{config.comparison_symbol} file", comparison_file
            ),
            overlap_range_analyzed=_overlap_range_summary(common_dates),
            overlapping_start_date=min(common_dates) if common_dates else None,
            overlapping_end_date=max(common_dates) if common_dates else None,
            trading_days_analyzed=len(common_dates),
            sample_description=_sample_description(len(common_dates)),
            trigger_time_label=_time_label(config.trigger_time),
            morning_windows_tested=config.morning_windows,
            outcome_windows_tested=[label for _id, label, _end in DEFAULT_OUTCOME_WINDOWS],
            setup_families=families,
            trigger_condition_summaries=condition_summaries,
            outcome_window_summaries=outcome_summaries,
            ranked_trigger_exit_combinations=ranked,
            strongest_examples=strongest,
            weakest_examples=weakest,
            giveback_hold_summary=giveback_hold_summary,
            best_current_research_clue=best_clue,
            examples_are_too_few=all(
                summary.matching_mornings < 15 for summary in outcome_summaries
            ),
            plain_english_bottom_line=bottom_line,
            what_to_study_next=_what_to_study_next(ranked),
        )


def spy_csgp_trigger_exit_config() -> PairMorningTriggerExitConfig:
    """Configured SPY/CSGP application of the generic pair engine."""

    return PairMorningTriggerExitConfig(
        study_name="SPY / CSGP Morning Divergence Trigger and Exit Study",
        primary_symbol="SPY",
        comparison_symbol="CSGP",
        relationship_name="Morning inverse relationship",
        primary_down_label="SPY down",
        primary_up_label="SPY up",
        comparison_stronger_label="CSGP stronger",
        comparison_weaker_label="CSGP weaker",
        primary_file_path=DEFAULT_SPY_RECENT_PATH,
        comparison_file_path=DEFAULT_CSGP_RECENT_PATH,
    )


def _trigger_definitions(
    config: PairMorningTriggerExitConfig,
) -> list[TriggerConditionDefinition]:
    down_family = f"{config.primary_down_label} / {config.comparison_stronger_label}"
    up_family = f"{config.primary_up_label} / {config.comparison_weaker_label}"
    return [
        TriggerConditionDefinition(
            condition_id="A1",
            family_id="primary_down_comparison_stronger",
            family_label=down_family,
            trigger_label=(
                f"{config.primary_down_label} at least 0.50% by {_time_label(config.trigger_time)} "
                f"while {config.comparison_symbol} is positive"
            ),
            primary_direction="down",
            primary_threshold_pct=0.50,
            comparison_rule="above_zero",
            favorable_direction="higher",
        ),
        TriggerConditionDefinition(
            condition_id="A2",
            family_id="primary_down_comparison_stronger",
            family_label=down_family,
            trigger_label=(
                f"{config.primary_down_label} at least 0.50% by {_time_label(config.trigger_time)} "
                f"while {config.comparison_symbol} is up at least 0.50%"
            ),
            primary_direction="down",
            primary_threshold_pct=0.50,
            comparison_rule="at_least",
            comparison_threshold_pct=0.50,
            favorable_direction="higher",
        ),
        TriggerConditionDefinition(
            condition_id="A3",
            family_id="primary_down_comparison_stronger",
            family_label=down_family,
            trigger_label=(
                f"{config.primary_down_label} at least 0.75% by {_time_label(config.trigger_time)} "
                f"while {config.comparison_symbol} is positive"
            ),
            primary_direction="down",
            primary_threshold_pct=0.75,
            comparison_rule="above_zero",
            favorable_direction="higher",
        ),
        TriggerConditionDefinition(
            condition_id="A4",
            family_id="primary_down_comparison_stronger",
            family_label=down_family,
            trigger_label=(
                f"{config.primary_down_label} at least 0.75% by {_time_label(config.trigger_time)} "
                f"while {config.comparison_symbol} is up at least 1.00%"
            ),
            primary_direction="down",
            primary_threshold_pct=0.75,
            comparison_rule="at_least",
            comparison_threshold_pct=1.00,
            favorable_direction="higher",
        ),
        TriggerConditionDefinition(
            condition_id="A5",
            family_id="primary_down_comparison_stronger",
            family_label=down_family,
            trigger_label=(
                f"{config.primary_down_label} at least 1.00% by {_time_label(config.trigger_time)} "
                f"while {config.comparison_symbol} is positive"
            ),
            primary_direction="down",
            primary_threshold_pct=1.00,
            comparison_rule="above_zero",
            favorable_direction="higher",
        ),
        TriggerConditionDefinition(
            condition_id="A6",
            family_id="primary_down_comparison_stronger",
            family_label=down_family,
            trigger_label=(
                f"{config.primary_down_label} at least 0.50% by {_time_label(config.trigger_time)} "
                f"while {config.comparison_symbol} is at least 1 point stronger"
            ),
            primary_direction="down",
            primary_threshold_pct=0.50,
            comparison_rule="spread",
            spread_threshold_pct=1.00,
            favorable_direction="higher",
        ),
        TriggerConditionDefinition(
            condition_id="B1",
            family_id="primary_up_comparison_weaker",
            family_label=up_family,
            trigger_label=(
                f"{config.primary_up_label} at least 0.50% by {_time_label(config.trigger_time)} "
                f"while {config.comparison_symbol} is negative"
            ),
            primary_direction="up",
            primary_threshold_pct=0.50,
            comparison_rule="below_zero",
            favorable_direction="lower",
        ),
        TriggerConditionDefinition(
            condition_id="B2",
            family_id="primary_up_comparison_weaker",
            family_label=up_family,
            trigger_label=(
                f"{config.primary_up_label} at least 0.50% by {_time_label(config.trigger_time)} "
                f"while {config.comparison_symbol} is down at least 0.50%"
            ),
            primary_direction="up",
            primary_threshold_pct=0.50,
            comparison_rule="at_most",
            comparison_threshold_pct=-0.50,
            favorable_direction="lower",
        ),
        TriggerConditionDefinition(
            condition_id="B3",
            family_id="primary_up_comparison_weaker",
            family_label=up_family,
            trigger_label=(
                f"{config.primary_up_label} at least 0.75% by {_time_label(config.trigger_time)} "
                f"while {config.comparison_symbol} is negative"
            ),
            primary_direction="up",
            primary_threshold_pct=0.75,
            comparison_rule="below_zero",
            favorable_direction="lower",
        ),
        TriggerConditionDefinition(
            condition_id="B4",
            family_id="primary_up_comparison_weaker",
            family_label=up_family,
            trigger_label=(
                f"{config.primary_up_label} at least 0.75% by {_time_label(config.trigger_time)} "
                f"while {config.comparison_symbol} is down at least 1.00%"
            ),
            primary_direction="up",
            primary_threshold_pct=0.75,
            comparison_rule="at_most",
            comparison_threshold_pct=-1.00,
            favorable_direction="lower",
        ),
        TriggerConditionDefinition(
            condition_id="B5",
            family_id="primary_up_comparison_weaker",
            family_label=up_family,
            trigger_label=(
                f"{config.primary_up_label} at least 1.00% by {_time_label(config.trigger_time)} "
                f"while {config.comparison_symbol} is negative"
            ),
            primary_direction="up",
            primary_threshold_pct=1.00,
            comparison_rule="below_zero",
            favorable_direction="lower",
        ),
        TriggerConditionDefinition(
            condition_id="B6",
            family_id="primary_up_comparison_weaker",
            family_label=up_family,
            trigger_label=(
                f"{config.primary_up_label} at least 0.50% by {_time_label(config.trigger_time)} "
                f"while {config.comparison_symbol} lags by at least 1 point"
            ),
            primary_direction="up",
            primary_threshold_pct=0.50,
            comparison_rule="spread",
            spread_threshold_pct=1.00,
            favorable_direction="lower",
        ),
    ]


def _matching_trigger_dates(
    definition: TriggerConditionDefinition,
    primary_bars: dict[date, list[_LocalBar]],
    comparison_bars: dict[date, list[_LocalBar]],
    common_dates: list[date],
    config: PairMorningTriggerExitConfig,
) -> dict[date, tuple[float, float]]:
    matches: dict[date, tuple[float, float]] = {}
    for trading_date in common_dates:
        primary_move = _window_return_pct(
            primary_bars[trading_date], DEFAULT_MORNING_START, config.trigger_time
        )
        comparison_move = _window_return_pct(
            comparison_bars[trading_date], DEFAULT_MORNING_START, config.trigger_time
        )
        if primary_move is None or comparison_move is None:
            continue
        if _matches_definition(definition, primary_move, comparison_move):
            matches[trading_date] = (round(primary_move, 4), round(comparison_move, 4))
    return matches


def _matches_definition(
    definition: TriggerConditionDefinition,
    primary_move: float,
    comparison_move: float,
) -> bool:
    if definition.primary_direction == "down":
        primary_matches = primary_move <= -definition.primary_threshold_pct
    else:
        primary_matches = primary_move >= definition.primary_threshold_pct
    if not primary_matches:
        return False
    if definition.comparison_rule == "above_zero":
        return comparison_move > 0
    if definition.comparison_rule == "below_zero":
        return comparison_move < 0
    if definition.comparison_rule == "at_least":
        return (
            definition.comparison_threshold_pct is not None
            and comparison_move >= definition.comparison_threshold_pct
        )
    if definition.comparison_rule == "at_most":
        return (
            definition.comparison_threshold_pct is not None
            and comparison_move <= definition.comparison_threshold_pct
        )
    if definition.primary_direction == "down":
        return (
            definition.spread_threshold_pct is not None
            and comparison_move - primary_move >= definition.spread_threshold_pct
        )
    return (
        definition.spread_threshold_pct is not None
        and primary_move - comparison_move >= definition.spread_threshold_pct
    )


def _outcome_summary(
    *,
    definition: TriggerConditionDefinition,
    trigger_examples: dict[date, tuple[float, float]],
    primary_bars: dict[date, list[_LocalBar]],
    comparison_bars: dict[date, list[_LocalBar]],
    outcome_window_id: str,
    outcome_window_label: str,
    outcome_end: time,
    config: PairMorningTriggerExitConfig,
) -> tuple[OutcomeWindowSummary, list[TriggerExample]]:
    examples: list[TriggerExample] = []
    for trading_date, (primary_move, comparison_move) in trigger_examples.items():
        outcome = _comparison_outcome(
            comparison_bars[trading_date],
            config.trigger_time,
            outcome_end,
            definition.favorable_direction,
            comparison_move,
        )
        if outcome is None:
            continue
        post_move, max_favorable, max_adverse, reached, gave_back, kept = outcome
        examples.append(
            TriggerExample(
                date=trading_date,
                condition_id=definition.condition_id,
                trigger_label=definition.trigger_label,
                family_label=definition.family_label,
                outcome_window=outcome_window_label,
                primary_morning_move=primary_move,
                comparison_morning_move=comparison_move,
                comparison_post_trigger_move=post_move,
                max_favorable_move=max_favorable,
                max_adverse_move=max_adverse,
                gave_back_half=gave_back,
                kept_half=kept,
                plain_english_summary=_example_summary(
                    trading_date,
                    config,
                    primary_move,
                    comparison_move,
                    post_move,
                    outcome_window_label,
                ),
            )
        )
    post_moves = [example.comparison_post_trigger_move for example in examples]
    favorable = [
        example
        for example in examples
        if _is_favorable(example.comparison_post_trigger_move, definition.favorable_direction)
    ]
    adverse = [
        example
        for example in examples
        if _is_adverse(example.comparison_post_trigger_move, definition.favorable_direction)
    ]
    best = _best_example(examples, definition.favorable_direction)
    worst = _worst_example(examples, definition.favorable_direction)
    threshold_counts = _threshold_counts(examples, definition.favorable_direction)
    rating = _rating(
        len(examples),
        _percent(len(favorable), len(examples)),
        _round_optional_median(post_moves),
        definition.favorable_direction,
    )
    summary = OutcomeWindowSummary(
        condition_id=definition.condition_id,
        trigger_label=definition.trigger_label,
        family_id=definition.family_id,
        family_label=definition.family_label,
        outcome_window_id=outcome_window_id,
        outcome_window_label=outcome_window_label,
        matching_mornings=len(examples),
        average_post_trigger_move=_round_optional_mean(post_moves),
        median_post_trigger_move=_round_optional_median(post_moves),
        favorable_count=len(favorable),
        favorable_percent=_percent(len(favorable), len(examples)),
        adverse_count=len(adverse),
        adverse_percent=_percent(len(adverse), len(examples)),
        best_date=best.date if best else None,
        worst_date=worst.date if worst else None,
        average_max_favorable_move=_round_optional_mean(
            example.max_favorable_move for example in examples
        ),
        average_max_adverse_move=_round_optional_mean(
            example.max_adverse_move for example in examples
        ),
        threshold_reached_counts=threshold_counts,
        gave_back_half_count=sum(1 for example in examples if example.gave_back_half),
        kept_half_count=sum(1 for example in examples if example.kept_half),
        sample_size_warning=_sample_size_warning(len(examples)),
        rating=rating,
        plain_english_summary=_outcome_plain_summary(
            definition.trigger_label,
            outcome_window_label,
            len(examples),
            len(favorable),
            rating,
        ),
    )
    return summary, examples


def _comparison_outcome(
    bars: list[_LocalBar],
    trigger_time: time,
    outcome_end: time,
    favorable_direction: Literal["higher", "lower"],
    comparison_morning_move: float,
) -> tuple[float, float, float, dict[str, bool], bool, bool] | None:
    start_bar = next((bar for bar in bars if bar.local_time >= trigger_time), None)
    if start_bar is None:
        return None
    window_bars = [
        bar
        for bar in bars
        if bar.timestamp >= start_bar.timestamp and bar.local_time <= outcome_end
    ]
    if not window_bars:
        return None
    end_bar = window_bars[-1]
    start_price = start_bar.close
    if start_price <= 0:
        return None
    post_move = ((end_bar.close - start_price) / start_price) * 100
    high_move = ((max(bar.high for bar in window_bars) - start_price) / start_price) * 100
    low_move = ((min(bar.low for bar in window_bars) - start_price) / start_price) * 100
    if favorable_direction == "higher":
        max_favorable = high_move
        max_adverse = low_move
    else:
        max_favorable = low_move
        max_adverse = high_move
    end_from_open = comparison_morning_move + post_move
    gave_back = False
    kept = False
    if favorable_direction == "higher" and comparison_morning_move > 0:
        kept = end_from_open >= comparison_morning_move * 0.5
        gave_back = end_from_open < comparison_morning_move * 0.5
    if favorable_direction == "lower" and comparison_morning_move < 0:
        kept = end_from_open <= comparison_morning_move * 0.5
        gave_back = end_from_open > comparison_morning_move * 0.5
    reached = {
        _threshold_label(threshold, favorable_direction): _threshold_reached(
            threshold, high_move, low_move, favorable_direction
        )
        for threshold in EXIT_THRESHOLDS
    }
    return (
        round(post_move, 4),
        round(max_favorable, 4),
        round(max_adverse, 4),
        reached,
        gave_back,
        kept,
    )


def _window_return_pct(bars: list[_LocalBar], start_time: time, end_time: time) -> float | None:
    start_bar = next((bar for bar in bars if bar.local_time >= start_time), None)
    end_candidates = [bar for bar in bars if bar.local_time <= end_time]
    end_bar = end_candidates[-1] if end_candidates else None
    if start_bar is None or end_bar is None or end_bar.timestamp < start_bar.timestamp:
        return None
    if start_bar.open <= 0:
        return None
    return ((end_bar.close - start_bar.open) / start_bar.open) * 100


def _condition_summaries(
    definitions: list[TriggerConditionDefinition],
    outcome_summaries: list[OutcomeWindowSummary],
) -> list[TriggerConditionSummary]:
    summaries: list[TriggerConditionSummary] = []
    for definition in definitions:
        matching = [
            summary
            for summary in outcome_summaries
            if summary.condition_id == definition.condition_id
        ]
        best = _best_outcome_summary(matching)
        examples_found = max((summary.matching_mornings for summary in matching), default=0)
        summaries.append(
            TriggerConditionSummary(
                condition_id=definition.condition_id,
                trigger_label=definition.trigger_label,
                family_id=definition.family_id,
                family_label=definition.family_label,
                examples_found=examples_found,
                best_outcome_window=best.outcome_window_label if best else "No outcome window yet",
                best_rating=best.rating if best else "Too few examples",
                plain_english_summary=_condition_plain_summary(
                    definition.trigger_label, examples_found, best
                ),
            )
        )
    return summaries


def _family_summaries(
    config: PairMorningTriggerExitConfig,
    condition_summaries: list[TriggerConditionSummary],
) -> list[SetupFamilySummary]:
    families: list[SetupFamilySummary] = []
    for family_id, family_label in [
        (
            "primary_down_comparison_stronger",
            f"{config.primary_down_label} / {config.comparison_stronger_label}",
        ),
        (
            "primary_up_comparison_weaker",
            f"{config.primary_up_label} / {config.comparison_weaker_label}",
        ),
    ]:
        conditions = [summary for summary in condition_summaries if summary.family_id == family_id]
        examples = sum(summary.examples_found for summary in conditions)
        if examples == 0:
            plain = f"{family_label}: no trigger examples in the local overlap."
        else:
            plain = f"{family_label}: {examples} trigger-window matches across tested conditions."
        families.append(
            SetupFamilySummary(
                family_id=family_id,
                family_label=family_label,
                trigger_time_label=_time_label(config.trigger_time),
                trigger_conditions=conditions,
                plain_english_summary=plain,
            )
        )
    return families


def _rank_outcomes(
    outcome_summaries: list[OutcomeWindowSummary],
) -> list[RankedTriggerExitCombination]:
    sorted_rows = sorted(
        outcome_summaries,
        key=lambda summary: (
            _rating_score(summary.rating),
            summary.matching_mornings,
            summary.favorable_percent or 0,
            abs(summary.median_post_trigger_move or 0),
        ),
        reverse=True,
    )
    ranked: list[RankedTriggerExitCombination] = []
    for index, summary in enumerate(sorted_rows[:12], start=1):
        ranked.append(
            RankedTriggerExitCombination(
                rank=index,
                condition_id=summary.condition_id,
                trigger_label=summary.trigger_label,
                outcome_window_label=summary.outcome_window_label,
                examples_found=summary.matching_mornings,
                favorable_percent=summary.favorable_percent,
                median_post_trigger_move=summary.median_post_trigger_move,
                average_max_favorable_move=summary.average_max_favorable_move,
                average_max_adverse_move=summary.average_max_adverse_move,
                sample_size_warning=summary.sample_size_warning,
                rating=summary.rating,
                plain_english_summary=summary.plain_english_summary,
            )
        )
    return ranked


def _rating(
    examples: int,
    favorable_percent: float | None,
    median_move: float | None,
    favorable_direction: Literal["higher", "lower"],
) -> str:
    if examples < 5:
        return "Too few examples"
    if favorable_percent is None or median_move is None:
        return "Mixed results / no clear answer"
    median_supportive = median_move > 0 if favorable_direction == "higher" else median_move < 0
    if examples < 15:
        if favorable_percent > 60 and median_supportive:
            return "Interesting but needs more history"
        return "Mixed results / no clear answer"
    if favorable_percent >= 60 and median_supportive:
        return "Interesting but needs more history"
    if favorable_percent < 35 and not median_supportive:
        return "Reject for now"
    return "Mixed results / no clear answer"


def _rating_score(rating: str) -> int:
    return {
        "Interesting but needs more history": 3,
        "Mixed results / no clear answer": 2,
        "Too few examples": 1,
        "Reject for now": 0,
    }.get(rating, 0)


def _sample_size_warning(examples: int) -> str:
    if examples < 5:
        return "Too few examples"
    if examples < 15:
        return "Small local sample"
    return "Still needs more history"


def _threshold_counts(
    examples: list[TriggerExample],
    favorable_direction: Literal["higher", "lower"],
) -> dict[str, int]:
    counts = {_threshold_label(threshold, favorable_direction): 0 for threshold in EXIT_THRESHOLDS}
    for example in examples:
        for threshold in EXIT_THRESHOLDS:
            label = _threshold_label(threshold, favorable_direction)
            if favorable_direction == "higher" and example.max_favorable_move >= threshold:
                counts[label] += 1
            if favorable_direction == "lower" and example.max_favorable_move <= -threshold:
                counts[label] += 1
    return counts


def _threshold_label(threshold: float, favorable_direction: Literal["higher", "lower"]) -> str:
    sign = "+" if favorable_direction == "higher" else "-"
    return f"Reached {sign}{threshold:.2f}% from trigger"


def _threshold_reached(
    threshold: float,
    high_move: float,
    low_move: float,
    favorable_direction: Literal["higher", "lower"],
) -> bool:
    if favorable_direction == "higher":
        return high_move >= threshold
    return low_move <= -threshold


def _strongest_and_weakest_examples(
    examples: list[TriggerExample],
    limit: int = 5,
) -> tuple[list[TriggerExample], list[TriggerExample]]:
    unique = _dedupe_examples(examples)
    strongest = sorted(unique, key=_example_strength, reverse=True)[:limit]
    weakest = sorted(unique, key=_example_strength)[:limit]
    return strongest, weakest


def _dedupe_examples(examples: list[TriggerExample]) -> list[TriggerExample]:
    seen: set[tuple[date, str, str]] = set()
    deduped: list[TriggerExample] = []
    for example in examples:
        key = (example.date, example.condition_id, example.outcome_window)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(example)
    return deduped


def _example_strength(example: TriggerExample) -> float:
    if "weaker" in example.family_label.lower():
        return -example.comparison_post_trigger_move
    return example.comparison_post_trigger_move


def _best_example(
    examples: list[TriggerExample],
    favorable_direction: Literal["higher", "lower"],
) -> TriggerExample | None:
    if not examples:
        return None
    if favorable_direction == "higher":
        return max(examples, key=lambda example: example.comparison_post_trigger_move)
    return min(examples, key=lambda example: example.comparison_post_trigger_move)


def _worst_example(
    examples: list[TriggerExample],
    favorable_direction: Literal["higher", "lower"],
) -> TriggerExample | None:
    if not examples:
        return None
    if favorable_direction == "higher":
        return min(examples, key=lambda example: example.comparison_post_trigger_move)
    return max(examples, key=lambda example: example.comparison_post_trigger_move)


def _best_outcome_summary(
    summaries: list[OutcomeWindowSummary],
) -> OutcomeWindowSummary | None:
    if not summaries:
        return None
    return sorted(
        summaries,
        key=lambda summary: (
            _rating_score(summary.rating),
            summary.matching_mornings,
            summary.favorable_percent or 0,
        ),
        reverse=True,
    )[0]


def _best_current_research_clue(ranked: list[RankedTriggerExitCombination]) -> str:
    interesting = [row for row in ranked if row.rating == "Interesting but needs more history"]
    if interesting:
        row = interesting[0]
        return (
            f"The best current clue is {row.trigger_label}, measured through "
            f"{row.outcome_window_label}. This is still a local sample and needs more history."
        )
    if ranked and ranked[0].examples_found > 0:
        row = ranked[0]
        return (
            f"The closest current clue is {row.trigger_label}, measured through "
            f"{row.outcome_window_label}, but the rating is {row.rating.lower()}."
        )
    return "EdgeLab did not find enough trigger examples to name a current clue."


def _bottom_line(
    ranked: list[RankedTriggerExitCombination],
    trading_days: int,
    sample_description: str,
) -> str:
    if trading_days == 0:
        return "EdgeLab cannot run this study until both local pair files overlap."
    if not ranked or ranked[0].examples_found == 0:
        return "EdgeLab found no trigger examples in the current local overlap."
    best = ranked[0]
    if best.rating == "Too few examples":
        return "EdgeLab found a few trigger examples, but not enough to judge the setup."
    if best.rating == "Interesting but needs more history":
        return (
            f"The best current clue is {best.trigger_label}, measured through "
            f"{best.outcome_window_label}. This is still a {sample_description.lower()} "
            "and needs more history."
        )
    if best.rating == "Reject for now":
        return (
            "The tested trigger conditions did not separate better mornings from worse mornings "
            "in this local sample."
        )
    return (
        "EdgeLab found both helpful and unhelpful post-trigger moves. The setup needs a "
        "narrower condition before it is worth expanding."
    )


def _what_to_study_next(ranked: list[RankedTriggerExitCombination]) -> list[str]:
    if not ranked or ranked[0].examples_found == 0:
        return [
            "Check whether the configured local files overlap.",
            "Try a broader local sample before narrowing trigger conditions.",
        ]
    best = ranked[0]
    if best.rating == "Interesting but needs more history":
        return [
            "Test the top clue on more matched local history.",
            "Check whether the same trigger behaves differently by weekday or gap size.",
            "Keep the same trigger time before adding more moving parts.",
        ]
    return [
        "Try a narrower version of the closest mixed setup.",
        "Separate the two setup families before adding more pair relationships.",
        "Do not treat this as a signal system.",
    ]


def _giveback_hold_summary(summaries: list[OutcomeWindowSummary]) -> str:
    examples = sum(summary.matching_mornings for summary in summaries)
    givebacks = sum(summary.gave_back_half_count for summary in summaries)
    kept = sum(summary.kept_half_count for summary in summaries)
    if examples == 0:
        return "No trigger examples had enough post-trigger data for giveback or hold behavior."
    return (
        f"Across tested trigger/window combinations, EdgeLab counted {kept} kept-half cases "
        f"and {givebacks} gave-back-half cases. This is evidence detail, not a decision rule."
    )


def _data_readiness_summary(
    primary_file: MorningDivergenceFileSummary,
    comparison_file: MorningDivergenceFileSummary,
    common_dates: list[date],
) -> str:
    if not primary_file.exists and not comparison_file.exists:
        return "Both configured pair files are missing locally."
    if not primary_file.exists:
        return f"{primary_file.symbol} file is missing locally."
    if not comparison_file.exists:
        return f"{comparison_file.symbol} file is missing locally."
    if not common_dates:
        return "Configured pair files exist, but their trading dates do not overlap."
    return (
        f"{primary_file.symbol} and {comparison_file.symbol} files overlap from "
        f"{min(common_dates)} to {max(common_dates)} with {len(common_dates)} trading days."
    )


def _outcome_plain_summary(
    trigger_label: str,
    window_label: str,
    examples: int,
    favorable_count: int,
    rating: str,
) -> str:
    if examples == 0:
        return f"{trigger_label}, through {window_label}: no matching examples."
    return (
        f"{trigger_label}, through {window_label}: {favorable_count} of {examples} examples "
        f"moved in the favorable direction. Rating: {rating}."
    )


def _condition_plain_summary(
    trigger_label: str,
    examples_found: int,
    best: OutcomeWindowSummary | None,
) -> str:
    if examples_found == 0:
        return f"{trigger_label}: no matching examples in the local overlap."
    if best is None:
        return f"{trigger_label}: examples found, but no outcome window could be measured."
    return (
        f"{trigger_label}: {examples_found} examples. Best current outcome window: "
        f"{best.outcome_window_label}, rated {best.rating}."
    )


def _example_summary(
    trading_date: date,
    config: PairMorningTriggerExitConfig,
    primary_move: float,
    comparison_move: float,
    post_move: float,
    outcome_window: str,
) -> str:
    return (
        f"{trading_date}: {config.primary_symbol} moved {primary_move:.2f}% by "
        f"{_time_label(config.trigger_time)}, {config.comparison_symbol} moved "
        f"{comparison_move:.2f}% by {_time_label(config.trigger_time)}, then "
        f"{config.comparison_symbol} moved {post_move:.2f}% during {outcome_window}."
    )


def _is_favorable(value: float, favorable_direction: Literal["higher", "lower"]) -> bool:
    return value > 0 if favorable_direction == "higher" else value < 0


def _is_adverse(value: float, favorable_direction: Literal["higher", "lower"]) -> bool:
    return value < 0 if favorable_direction == "higher" else value > 0


def _percent(count: int, total: int) -> float | None:
    if total == 0:
        return None
    return round((count / total) * 100, 1)


def _round_optional_mean(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(mean(present), 4)


def _round_optional_median(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return round(median(present), 4)


def _time_label(value: time) -> str:
    return value.strftime("%H:%M").lstrip("0")
