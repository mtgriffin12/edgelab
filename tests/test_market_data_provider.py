from pathlib import Path

from edgelab.data.market_data import LocalFixtureMarketDataProvider


def write_fixture(fixture_dir: Path, symbol: str, rows: list[str]) -> None:
    fixture_dir.mkdir(parents=True, exist_ok=True)
    header = "symbol,timestamp,interval,open,high,low,close,volume,adjusted_close,source"
    (fixture_dir / f"{symbol.lower()}.csv").write_text(
        "\n".join([header, *rows]) + "\n",
        encoding="utf-8",
    )


def test_fixture_provider_lists_available_symbols() -> None:
    provider = LocalFixtureMarketDataProvider()

    assert provider.list_available_symbols() == ["AAPL", "QQQ", "SPY"]


def test_fixture_provider_loads_bars() -> None:
    provider = LocalFixtureMarketDataProvider()

    data = provider.load_bars("spy")

    assert data.symbol == "SPY"
    assert len(data.bars) == 5
    assert data.quality_issues == []


def test_fixture_provider_reports_missing_symbol() -> None:
    provider = LocalFixtureMarketDataProvider()

    data = provider.load_bars("missing")

    assert data.bars == []
    assert data.quality_issues[0].code == "missing_symbol"


def test_fixture_provider_reports_invalid_ohlc_and_negative_volume(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "bad",
        [
            "BAD,2024-01-02T00:00:00Z,1d,10,9,8,10,100,10,synthetic_fixture",
            "BAD,2024-01-03T00:00:00Z,1d,10,11,9,10,-1,10,synthetic_fixture",
        ],
    )
    provider = LocalFixtureMarketDataProvider(tmp_path)

    data = provider.load_bars("bad")

    assert data.bars == []
    assert [issue.code for issue in data.quality_issues].count("invalid_bar") == 2
    assert any(issue.code == "empty_dataset" for issue in data.quality_issues)


def test_fixture_provider_detects_duplicate_rows(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "dup",
        [
            "DUP,2024-01-02T00:00:00Z,1d,10,11,9,10,100,10,synthetic_fixture",
            "DUP,2024-01-02T00:00:00Z,1d,10,11,9,10,100,10,synthetic_fixture",
        ],
    )
    provider = LocalFixtureMarketDataProvider(tmp_path)

    data = provider.load_bars("dup")

    assert any(issue.code == "duplicate_bar" for issue in data.quality_issues)


def test_fixture_provider_detects_unsorted_timestamps(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "sort",
        [
            "SORT,2024-01-03T00:00:00Z,1d,10,11,9,10,100,10,synthetic_fixture",
            "SORT,2024-01-02T00:00:00Z,1d,10,11,9,10,100,10,synthetic_fixture",
        ],
    )
    provider = LocalFixtureMarketDataProvider(tmp_path)

    data = provider.load_bars("sort")

    assert any(issue.code == "unsorted_timestamps" for issue in data.quality_issues)


def test_fixture_provider_generates_summary() -> None:
    provider = LocalFixtureMarketDataProvider()

    summary = provider.summarize_symbol("qqq")

    assert summary.symbol == "QQQ"
    assert summary.row_count == 5
    assert summary.min_close == 403.10
    assert summary.max_close == 416.25
    assert summary.total_volume == 270_300_000
    assert summary.quality_issue_count == 0
