from pathlib import Path

from edgelab.intraday.fixtures import LocalIntradayFixtureProvider


def write_fixture(fixture_dir: Path, name: str, rows: list[str]) -> None:
    fixture_dir.mkdir(parents=True, exist_ok=True)
    header = (
        "symbol,timestamp,interval,open,high,low,close,volume,session_type,"
        "session_id,source,ingested_at"
    )
    (fixture_dir / name).write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


def test_fixture_provider_lists_symbols_dynamically() -> None:
    provider = LocalIntradayFixtureProvider()

    assert provider.list_available_symbols() == ["ES_SYN", "GEN_SYN", "NQ_SYN"]


def test_fixture_provider_lists_sessions_dynamically() -> None:
    provider = LocalIntradayFixtureProvider()

    sessions = provider.list_available_sessions("ES_SYN")

    assert {session["session_id"] for session in sessions} >= {
        "es-first-hour-synthetic",
        "es-choppy-no-trade-synthetic",
        "es-opening-failure-short-context-synthetic",
    }


def test_fixture_provider_loads_generic_symbol() -> None:
    provider = LocalIntradayFixtureProvider()

    bars, issues = provider.load_bars("GEN_SYN")

    assert len(bars) >= 10
    assert issues == []
    assert bars[0].symbol == "GEN_SYN"


def test_fixture_provider_handles_missing_fixture() -> None:
    provider = LocalIntradayFixtureProvider()

    bars, issues = provider.load_bars("MISSING")

    assert bars == []
    assert issues[0].code == "missing_symbol"


def test_fixture_provider_detects_duplicate_unsorted_and_invalid_bars(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "bad.csv",
        [
            "BAD,2024-01-03T15:31:00Z,one_minute,10,11,9,10,100,regular_first_hour,bad-session,synthetic,2024-01-03T15:30:00Z",
            "BAD,2024-01-03T15:30:00Z,one_minute,10,11,9,10,100,regular_first_hour,bad-session,synthetic,2024-01-03T15:30:00Z",
            "BAD,2024-01-03T15:30:00Z,one_minute,10,11,9,10,100,regular_first_hour,bad-session,synthetic,2024-01-03T15:30:00Z",
            "BAD,2024-01-03T15:32:00Z,one_minute,10,9,8,10,-1,regular_first_hour,bad-session,synthetic,2024-01-03T15:30:00Z",
        ],
    )
    provider = LocalIntradayFixtureProvider(tmp_path)

    _bars, issues = provider.load_bars("BAD", "bad-session")
    issue_codes = [issue.code for issue in issues]

    assert "duplicate_bar" in issue_codes
    assert "unsorted_timestamps" in issue_codes
    assert "invalid_bar" in issue_codes
