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
