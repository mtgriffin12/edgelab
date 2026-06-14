from pathlib import Path

REQUIRED_DOCS = [
    "AGENTS.md",
    "README.md",
    "docs/product/trading-research-agent-brief.md",
    "docs/product/ux-principles.md",
    "docs/product/plain-english-ux-language.md",
    "docs/product/operating-model.md",
    "docs/architecture/system-architecture.md",
    "docs/architecture/data-architecture.md",
    "docs/architecture/cloud-readiness.md",
    "docs/domain/strategy-research-principles.md",
    "docs/domain/strategy-discovery-lab.md",
    "docs/domain/strategy-ranking-engine.md",
    "docs/domain/candidate-equity-screener.md",
    "docs/domain/model-portfolio-engine.md",
    "docs/domain/intraday-index-futures-research-spike.md",
    "docs/domain/historical-intraday-data-and-replay.md",
    "docs/domain/sentiment-intelligence-layer.md",
    "docs/domain/backtesting-principles.md",
    "docs/risk/risk-governance.md",
    "docs/implementation/phase-plan.md",
    "docs/implementation/decision-log.md",
]


def test_required_docs_exist() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    missing = [doc for doc in REQUIRED_DOCS if not (repo_root / doc).is_file()]

    assert missing == []


def test_historical_intraday_doc_includes_csv_format_and_data_boundary() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    content = (repo_root / "docs/domain/historical-intraday-data-and-replay.md").read_text()

    assert "symbol,raw_timestamp,source_timezone,interval,open,high,low,close,volume" in content
    assert "data/raw/" in content
    assert "data/processed/" in content
    assert "Real-money status is always Not allowed" in content
    assert "Phase 7X-2B" in content
    assert "Phase 7X-2D" in content
    assert "Phase 7X-2E" in content
    assert "FirstRate" in content
    assert "first-hour completeness" in content.lower()
    assert "data/raw/historical_intraday/firstratedata/" in content
    assert "without future knowledge" in content
