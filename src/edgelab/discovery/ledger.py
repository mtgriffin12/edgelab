"""In-memory experiment ledger scaffolding."""

from datetime import UTC, datetime

from edgelab.discovery.schema import ExperimentLedgerEntry


class ExperimentLedger:
    """Read-only in-memory experiment ledger."""

    def __init__(self, entries: list[ExperimentLedgerEntry] | None = None) -> None:
        self._entries = entries or []

    def list_entries(self) -> list[ExperimentLedgerEntry]:
        """Return ledger entries."""

        return list(self._entries)

    def export_all(self) -> list[dict[str, object]]:
        """Export ledger entries as JSON-friendly dictionaries."""

        return [entry.model_dump(mode="json") for entry in self.list_entries()]

    @classmethod
    def with_samples(cls) -> "ExperimentLedger":
        """Create a ledger with scaffold entries."""

        return cls(list(SAMPLE_LEDGER_ENTRIES))


SAMPLE_LEDGER_ENTRIES: tuple[ExperimentLedgerEntry, ...] = (
    ExperimentLedgerEntry(
        experiment_id="exp-rsp-baseline-001",
        discovery_id="relative-strength-pullback",
        strategy_id="relative-strength-pullback",
        experiment_type="baseline_comparison_scaffold",
        hypothesis=(
            "Relative strength pullbacks should beat a plain momentum continuation baseline."
        ),
        baseline_compared="Plain momentum continuation",
        data_used="Synthetic local fixture data only",
        result_summary="Not run. Scaffold entry records the comparison discipline.",
        outcome="not_run",
        lessons_learned=["A baseline comparison is required before deeper trust."],
        created_at=datetime(2026, 5, 28, tzinfo=UTC),
    ),
    ExperimentLedgerEntry(
        experiment_id="exp-social-euphoria-001",
        discovery_id="social-euphoria-without-price-confirmation",
        experiment_type="novel_hypothesis_scaffold",
        hypothesis="Crowd excitement without price confirmation may flag fragile interest.",
        baseline_compared="Simple momentum avoidance",
        data_used="Synthetic sentiment fixtures only",
        result_summary="Not run. Needs future point-in-time mood plus price validation.",
        outcome="not_run",
        lessons_learned=["Novel ideas start with higher overfitting risk."],
        created_at=datetime(2026, 5, 28, tzinfo=UTC),
    ),
)
