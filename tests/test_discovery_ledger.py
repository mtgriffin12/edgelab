from edgelab.discovery.ledger import ExperimentLedger


def test_experiment_ledger_samples_are_scaffold_only() -> None:
    ledger = ExperimentLedger.with_samples()
    entries = ledger.list_entries()

    assert entries
    assert all(entry.outcome == "not_run" for entry in entries)
    assert all(
        "not run" in entry.result_summary.lower() or "scaffold" in entry.result_summary.lower()
        for entry in entries
    )


def test_experiment_ledger_exports_dictionaries() -> None:
    ledger = ExperimentLedger.with_samples()

    exported = ledger.export_all()

    assert isinstance(exported[0], dict)
    assert "experiment_id" in exported[0]
