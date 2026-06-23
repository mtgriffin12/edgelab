"""Local-only MarketData.app downloader for SPY/CSGP research CSVs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from edgelab.intraday.schema import normalize_symbol

MARKETDATA_APP_TOKEN_ENV = "MARKETDATA_APP_TOKEN"
MARKETDATA_APP_CANDLES_BASE_URL = "https://api.marketdata.app/v1/stocks/candles"
DEFAULT_MARKETDATA_OUTPUT_DIR = Path("data/raw/historical_intraday/firstratedata")
TARGET_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
MARKETDATA_RESPONSE_COLUMNS = ["t", "o", "h", "l", "c", "v"]
NEW_YORK = ZoneInfo("America/New_York")
REGULAR_SESSION_START = time(9, 30)
REGULAR_SESSION_END = time(16, 0)


@dataclass(frozen=True)
class MarketDataAppRequestPlan:
    """One planned MarketData.app candle request."""

    symbol: str
    start_date: date
    end_date: date
    output_path: Path
    url: str
    params: dict[str, str]
    estimated_candles: int
    estimated_credits: int
    regular_hours_only: bool


@dataclass(frozen=True)
class MarketDataAppDownloadPlan:
    """Offline summary of planned MarketData.app requests."""

    requests: list[MarketDataAppRequestPlan]
    total_estimated_candles: int
    total_estimated_credits: int
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"


@dataclass(frozen=True)
class NormalizedCandle:
    """One normalized OHLCV candle."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class NormalizationResult:
    """Provider response normalization result."""

    rows: list[NormalizedCandle]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class NormalizedFileSummary:
    """Shape and range summary for one normalized CSV file."""

    path: Path
    exists: bool
    symbol: str | None
    row_count: int
    first_timestamp: datetime | None
    last_timestamp: datetime | None
    trading_dates: set[date]
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PairValidationResult:
    """Readiness check for paired SPY/CSGP normalized CSV files."""

    spy_summary: NormalizedFileSummary
    csgp_summary: NormalizedFileSummary
    overlapping_start: datetime | None
    overlapping_end: datetime | None
    common_trading_dates: int
    spy_only_dates: int
    csgp_only_dates: int
    suitable_for_morning_divergence_study: bool
    plain_english_summary: str
    research_only_status: str = "Research only"
    real_money_status: str = "Not allowed"


def token_is_present(env: Mapping[str, str] | None = None) -> bool:
    """Return whether the MarketData.app token is present without exposing it."""

    source = env if env is not None else os.environ
    return bool(source.get(MARKETDATA_APP_TOKEN_ENV, "").strip())


def read_marketdata_token(env: Mapping[str, str] | None = None) -> str:
    """Read the MarketData.app token at call time."""

    source = env if env is not None else os.environ
    token = source.get(MARKETDATA_APP_TOKEN_ENV, "").strip()
    if not token:
        raise ValueError(
            f"{MARKETDATA_APP_TOKEN_ENV} is required for a real MarketData.app download. "
            "Dry-run mode does not require it."
        )
    return token


def validate_requested_symbols(symbols: Sequence[str]) -> list[str]:
    """Normalize requested symbols and reject empty or unusual values."""

    normalized = [normalize_symbol(symbol) for symbol in symbols]
    if not normalized:
        raise ValueError("At least one symbol is required.")
    unique_symbols = list(dict.fromkeys(normalized))
    for symbol in unique_symbols:
        if not symbol or len(symbol) > 12:
            raise ValueError(f"Unsupported symbol {symbol!r}.")
        if not all(character.isalnum() or character in {".", "-"} for character in symbol):
            raise ValueError(f"Unsupported symbol {symbol!r}.")
    return unique_symbols


def calculate_date_window(
    *,
    months: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    today: date | None = None,
) -> tuple[date, date]:
    """Return the requested date window."""

    if (start_date is None) != (end_date is None):
        raise ValueError("Use both --start and --end, or use --months.")
    if start_date is not None and end_date is not None:
        if start_date > end_date:
            raise ValueError("Start date must be on or before end date.")
        return start_date, end_date

    selected_months = months or 12
    if selected_months not in {12, 18, 24}:
        raise ValueError("Months must be one of 12, 18, or 24.")
    selected_end = today or date.today()
    selected_start = _subtract_months(selected_end, selected_months)
    return selected_start, selected_end


def build_request_url(symbol: str, *, resolution: str = "1") -> str:
    """Build a MarketData.app historical stock candle URL without credentials."""

    normalized_symbol = validate_requested_symbols([symbol])[0]
    return f"{MARKETDATA_APP_CANDLES_BASE_URL}/{resolution}/{normalized_symbol}/"


def build_request_params(
    *,
    start_date: date,
    end_date: date,
    regular_hours_only: bool = True,
) -> dict[str, str]:
    """Build safe request params without credentials."""

    return {
        "from": start_date.isoformat(),
        "to": end_date.isoformat(),
        "extended": "false" if regular_hours_only else "true",
        "adjustsplits": "false",
    }


def output_path_for_symbol(output_dir: Path, symbol: str) -> Path:
    """Return the normalized output filename for one symbol."""

    normalized_symbol = validate_requested_symbols([symbol])[0]
    return output_dir / f"{normalized_symbol}_recent_1min.csv"


def estimate_candle_usage(
    *,
    start_date: date,
    end_date: date,
    symbol_count: int,
    regular_hours_only: bool = True,
) -> tuple[int, int]:
    """Estimate requested candles and credits."""

    minutes_per_day = 390 if regular_hours_only else 960
    trading_days = _weekday_count(start_date, end_date)
    estimated_candles = trading_days * minutes_per_day * symbol_count
    estimated_credits = math.ceil(estimated_candles / 1000)
    return estimated_candles, estimated_credits


def build_download_plan(
    *,
    symbols: Sequence[str],
    months: int | None = 12,
    start_date: date | None = None,
    end_date: date | None = None,
    output_dir: Path = DEFAULT_MARKETDATA_OUTPUT_DIR,
    regular_hours_only: bool = True,
    today: date | None = None,
) -> MarketDataAppDownloadPlan:
    """Build an offline plan for MarketData.app requests."""

    requested_symbols = validate_requested_symbols(symbols)
    selected_start, selected_end = calculate_date_window(
        months=months,
        start_date=start_date,
        end_date=end_date,
        today=today,
    )
    requests: list[MarketDataAppRequestPlan] = []
    for symbol in requested_symbols:
        estimated_candles, estimated_credits = estimate_candle_usage(
            start_date=selected_start,
            end_date=selected_end,
            symbol_count=1,
            regular_hours_only=regular_hours_only,
        )
        requests.append(
            MarketDataAppRequestPlan(
                symbol=symbol,
                start_date=selected_start,
                end_date=selected_end,
                output_path=output_path_for_symbol(output_dir, symbol),
                url=build_request_url(symbol),
                params=build_request_params(
                    start_date=selected_start,
                    end_date=selected_end,
                    regular_hours_only=regular_hours_only,
                ),
                estimated_candles=estimated_candles,
                estimated_credits=estimated_credits,
                regular_hours_only=regular_hours_only,
            )
        )
    return MarketDataAppDownloadPlan(
        requests=requests,
        total_estimated_candles=sum(item.estimated_candles for item in requests),
        total_estimated_credits=sum(item.estimated_credits for item in requests),
    )


def fetch_marketdata_candles(
    plan: MarketDataAppRequestPlan,
    *,
    token: str,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """Fetch one MarketData.app response. This is called only by explicit CLI download."""

    encoded_params = urlencode(plan.params)
    request = Request(
        f"{plan.url}?{encoded_params}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "EdgeLab-local-research/0.1",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            if response.status not in {200, 203}:
                raise RuntimeError(f"MarketData.app returned HTTP {response.status}.")
            payload = response.read().decode("utf-8")
    except HTTPError as error:
        raise RuntimeError(f"MarketData.app returned HTTP {error.code}.") from error
    except URLError as error:
        raise RuntimeError(f"MarketData.app request failed: {error.reason}") from error
    decoded = json.loads(payload)
    if not isinstance(decoded, dict):
        raise ValueError("MarketData.app response was not a JSON object.")
    return decoded


def normalize_marketdata_response(
    payload: Mapping[str, Any],
    *,
    regular_hours_only: bool = True,
) -> NormalizationResult:
    """Convert a MarketData.app candle payload into normalized rows."""

    warnings: list[str] = []
    status = str(payload.get("s", "ok"))
    if status == "no_data":
        return NormalizationResult(rows=[], warnings=["Provider returned no_data."])
    if status == "error":
        message = str(payload.get("errmsg", "Provider returned an error."))
        return NormalizationResult(rows=[], warnings=[message])

    raw_items = _extract_candle_items(payload)
    rows: list[NormalizedCandle] = []
    seen_timestamps: set[datetime] = set()
    for index, raw_item in enumerate(raw_items, start=1):
        parsed = _parse_candle(raw_item, index)
        if isinstance(parsed, str):
            warnings.append(parsed)
            continue
        if regular_hours_only and not _is_regular_hours(parsed.timestamp):
            continue
        if parsed.timestamp in seen_timestamps:
            warnings.append(
                f"Duplicate timestamp {format_timestamp(parsed.timestamp)} was skipped."
            )
            continue
        seen_timestamps.add(parsed.timestamp)
        rows.append(parsed)

    return NormalizationResult(
        rows=sorted(rows, key=lambda item: item.timestamp),
        warnings=warnings,
    )


def write_normalized_csv(
    path: Path,
    rows: Sequence[NormalizedCandle],
    *,
    overwrite: bool = False,
) -> NormalizedFileSummary:
    """Write normalized candles to CSV."""

    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists. Use --overwrite to replace it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=TARGET_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "timestamp": format_timestamp(row.timestamp),
                    "open": _format_number(row.open),
                    "high": _format_number(row.high),
                    "low": _format_number(row.low),
                    "close": _format_number(row.close),
                    "volume": str(row.volume),
                }
            )
    return validate_normalized_csv(path)


def validate_normalized_csv(path: Path) -> NormalizedFileSummary:
    """Validate one normalized CSV file and summarize its shape."""

    if not path.exists():
        return NormalizedFileSummary(
            path=path,
            exists=False,
            symbol=_symbol_from_recent_path(path),
            row_count=0,
            first_timestamp=None,
            last_timestamp=None,
            trading_dates=set(),
            warnings=[f"{path} does not exist."],
        )

    warnings: list[str] = []
    timestamps: list[datetime] = []
    trading_dates: set[date] = set()
    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_columns = set(TARGET_COLUMNS) - set(reader.fieldnames or [])
        if missing_columns:
            warnings.append(f"Missing normalized column(s): {', '.join(sorted(missing_columns))}.")
        for row_number, row in enumerate(reader, start=2):
            try:
                timestamp = _parse_provider_timestamp(row.get("timestamp"))
                _parse_required_float(row.get("open"), "open", row_number)
                _parse_required_float(row.get("high"), "high", row_number)
                _parse_required_float(row.get("low"), "low", row_number)
                _parse_required_float(row.get("close"), "close", row_number)
                _parse_required_volume(row.get("volume"), row_number)
            except ValueError as error:
                warnings.append(str(error))
                continue
            timestamps.append(timestamp)
            trading_dates.add(timestamp.astimezone(NEW_YORK).date())

    sorted_timestamps = sorted(timestamps)
    return NormalizedFileSummary(
        path=path,
        exists=True,
        symbol=_symbol_from_recent_path(path),
        row_count=len(timestamps),
        first_timestamp=sorted_timestamps[0] if sorted_timestamps else None,
        last_timestamp=sorted_timestamps[-1] if sorted_timestamps else None,
        trading_dates=trading_dates,
        warnings=warnings,
    )


def validate_pair(spy_path: Path, csgp_path: Path) -> PairValidationResult:
    """Compare two normalized SPY/CSGP files."""

    spy_summary = validate_normalized_csv(spy_path)
    csgp_summary = validate_normalized_csv(csgp_path)
    overlapping_start = _max_optional_datetime(
        [spy_summary.first_timestamp, csgp_summary.first_timestamp]
    )
    overlapping_end = _min_optional_datetime(
        [spy_summary.last_timestamp, csgp_summary.last_timestamp]
    )
    common_dates = spy_summary.trading_dates & csgp_summary.trading_dates
    spy_only_dates = spy_summary.trading_dates - csgp_summary.trading_dates
    csgp_only_dates = csgp_summary.trading_dates - spy_summary.trading_dates
    suitable = (
        spy_summary.exists
        and csgp_summary.exists
        and not spy_summary.warnings
        and not csgp_summary.warnings
        and overlapping_start is not None
        and overlapping_end is not None
        and overlapping_start <= overlapping_end
        and len(common_dates) > 0
    )
    return PairValidationResult(
        spy_summary=spy_summary,
        csgp_summary=csgp_summary,
        overlapping_start=overlapping_start,
        overlapping_end=overlapping_end,
        common_trading_dates=len(common_dates),
        spy_only_dates=len(spy_only_dates),
        csgp_only_dates=len(csgp_only_dates),
        suitable_for_morning_divergence_study=suitable,
        plain_english_summary=_pair_summary(
            spy_summary,
            csgp_summary,
            len(common_dates),
            suitable,
        ),
    )


def run_download_plan(
    plan: MarketDataAppDownloadPlan,
    *,
    token: str,
    overwrite: bool = False,
) -> list[NormalizedFileSummary]:
    """Run an explicit local download plan."""

    summaries: list[NormalizedFileSummary] = []
    for request_plan in plan.requests:
        payload = fetch_marketdata_candles(request_plan, token=token)
        normalized = normalize_marketdata_response(
            payload,
            regular_hours_only=request_plan.regular_hours_only,
        )
        if normalized.warnings and not normalized.rows:
            raise ValueError("; ".join(normalized.warnings))
        summaries.append(
            write_normalized_csv(
                request_plan.output_path,
                normalized.rows,
                overwrite=overwrite,
            )
        )
    return summaries


def format_timestamp(value: datetime) -> str:
    """Format timestamps consistently for normalized CSV output."""

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the local MarketData.app downloader CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.validate_pair:
        result = validate_pair(Path(args.validate_pair[0]), Path(args.validate_pair[1]))
        _print_pair_validation(result)
        return 0 if result.suitable_for_morning_divergence_study else 1

    start_date = date.fromisoformat(args.start) if args.start else None
    end_date = date.fromisoformat(args.end) if args.end else None
    output_dir = Path(args.output_dir)
    plan = build_download_plan(
        symbols=args.symbols,
        months=args.months,
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir,
        regular_hours_only=args.regular_hours_only,
    )
    _print_plan(plan, dry_run=args.dry_run)
    if args.dry_run:
        return 0

    token = read_marketdata_token()
    summaries = run_download_plan(plan, token=token, overwrite=args.overwrite)
    for summary in summaries:
        _print_file_summary(summary)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download MarketData.app 1-minute candles into ignored local EdgeLab CSV files."
        )
    )
    parser.add_argument("--symbols", nargs="+", default=["SPY", "CSGP"])
    parser.add_argument("--months", type=int, default=12, choices=[12, 18, 24])
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--output-dir", default=str(DEFAULT_MARKETDATA_OUTPUT_DIR))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--regular-hours-only", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--validate-pair", nargs=2, metavar=("SPY_CSV", "CSGP_CSV"))
    return parser


def _print_plan(plan: MarketDataAppDownloadPlan, *, dry_run: bool) -> None:
    mode = "Dry run only. No MarketData.app call was made." if dry_run else "Download mode."
    print(mode)
    print(f"Research-only status: {plan.research_only_status}")
    print(f"Real-money status: {plan.real_money_status}")
    print(f"Estimated candles: {plan.total_estimated_candles}")
    print(f"Estimated credits: {plan.total_estimated_credits}")
    for request_plan in plan.requests:
        print(f"- {request_plan.symbol}")
        print(f"  URL: {request_plan.url}")
        print(f"  Params: {request_plan.params}")
        print(f"  Output: {request_plan.output_path}")
        print(f"  Estimated candles: {request_plan.estimated_candles}")
        print(f"  Estimated credits: {request_plan.estimated_credits}")


def _print_file_summary(summary: NormalizedFileSummary) -> None:
    print(f"Output: {summary.path}")
    print(f"Rows: {summary.row_count}")
    print(f"First timestamp: {summary.first_timestamp}")
    print(f"Last timestamp: {summary.last_timestamp}")
    if summary.warnings:
        print(f"Warnings: {'; '.join(summary.warnings)}")


def _print_pair_validation(result: PairValidationResult) -> None:
    print(result.plain_english_summary)
    print(f"SPY first timestamp: {result.spy_summary.first_timestamp}")
    print(f"SPY last timestamp: {result.spy_summary.last_timestamp}")
    print(f"SPY rows: {result.spy_summary.row_count}")
    print(f"CSGP first timestamp: {result.csgp_summary.first_timestamp}")
    print(f"CSGP last timestamp: {result.csgp_summary.last_timestamp}")
    print(f"CSGP rows: {result.csgp_summary.row_count}")
    print(f"Common trading dates: {result.common_trading_dates}")
    print(f"SPY-only dates: {result.spy_only_dates}")
    print(f"CSGP-only dates: {result.csgp_only_dates}")
    print(f"Suitable for future study: {result.suitable_for_morning_divergence_study}")
    print(f"Real-money status: {result.real_money_status}")


def _extract_candle_items(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if all(column in payload for column in MARKETDATA_RESPONSE_COLUMNS):
        arrays = [payload[column] for column in MARKETDATA_RESPONSE_COLUMNS]
        if not all(isinstance(array, Sequence) and not isinstance(array, str) for array in arrays):
            raise ValueError("MarketData.app array response fields must be arrays.")
        lengths = {len(array) for array in arrays}
        if len(lengths) != 1:
            raise ValueError("MarketData.app array response fields have mismatched lengths.")
        return [
            {
                "t": payload["t"][index],
                "o": payload["o"][index],
                "h": payload["h"][index],
                "l": payload["l"][index],
                "c": payload["c"][index],
                "v": payload["v"][index],
            }
            for index in range(lengths.pop())
        ]

    for key in ("candles", "data", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            if not all(isinstance(item, Mapping) for item in value):
                raise ValueError(f"Provider field {key!r} must contain objects.")
            return value
    raise ValueError("MarketData.app response did not contain candle arrays or objects.")


def _parse_candle(raw_item: Mapping[str, Any], row_number: int) -> NormalizedCandle | str:
    try:
        timestamp = _parse_provider_timestamp(raw_item.get("t") or raw_item.get("timestamp"))
        open_price = _parse_required_float(
            raw_item.get("o") or raw_item.get("open"), "open", row_number
        )
        high_price = _parse_required_float(
            raw_item.get("h") or raw_item.get("high"), "high", row_number
        )
        low_price = _parse_required_float(
            raw_item.get("l") or raw_item.get("low"), "low", row_number
        )
        close_price = _parse_required_float(
            raw_item.get("c") or raw_item.get("close"),
            "close",
            row_number,
        )
        volume = _parse_required_volume(raw_item.get("v") or raw_item.get("volume"), row_number)
    except ValueError as error:
        return str(error)
    return NormalizedCandle(
        timestamp=timestamp,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
    )


def _parse_provider_timestamp(raw_value: Any) -> datetime:
    if raw_value is None or raw_value == "":
        raise ValueError("Missing timestamp.")
    if isinstance(raw_value, int | float):
        return datetime.fromtimestamp(raw_value, tz=UTC)
    if isinstance(raw_value, str):
        stripped = raw_value.strip()
        if not stripped:
            raise ValueError("Missing timestamp.")
        if stripped.isdigit():
            return datetime.fromtimestamp(int(stripped), tz=UTC)
        try:
            parsed = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"Timestamp {raw_value!r} could not be parsed.") from error
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=NEW_YORK)
        return parsed.astimezone(UTC)
    raise ValueError(f"Timestamp {raw_value!r} could not be parsed.")


def _parse_required_float(raw_value: Any, field_name: str, row_number: int) -> float:
    if raw_value is None or raw_value == "":
        raise ValueError(f"Row {row_number} is missing {field_name}.")
    try:
        return float(raw_value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Row {row_number} has invalid {field_name}.") from error


def _parse_required_volume(raw_value: Any, row_number: int) -> int:
    if raw_value is None or raw_value == "":
        raise ValueError(f"Row {row_number} is missing volume.")
    try:
        volume = int(float(raw_value))
    except (TypeError, ValueError) as error:
        raise ValueError(f"Row {row_number} has invalid volume.") from error
    if volume < 0:
        raise ValueError(f"Row {row_number} has negative volume.")
    return volume


def _is_regular_hours(timestamp: datetime) -> bool:
    local_time = timestamp.astimezone(NEW_YORK).time()
    return REGULAR_SESSION_START <= local_time < REGULAR_SESSION_END


def _format_number(value: float) -> str:
    return f"{value:.10f}".rstrip("0").rstrip(".")


def _subtract_months(value: date, months: int) -> date:
    target_month = value.month - months
    target_year = value.year
    while target_month <= 0:
        target_month += 12
        target_year -= 1
    day = min(value.day, _days_in_month(target_year, target_month))
    return date(target_year, target_month, day)


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - timedelta(days=1)).day


def _weekday_count(start_date: date, end_date: date) -> int:
    current = start_date
    count = 0
    while current <= end_date:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def _max_optional_datetime(values: Iterable[datetime | None]) -> datetime | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _min_optional_datetime(values: Iterable[datetime | None]) -> datetime | None:
    present = [value for value in values if value is not None]
    return min(present) if present else None


def _symbol_from_recent_path(path: Path) -> str | None:
    if not path.name:
        return None
    return path.stem.split("_", maxsplit=1)[0].upper()


def _pair_summary(
    spy_summary: NormalizedFileSummary,
    csgp_summary: NormalizedFileSummary,
    common_dates: int,
    suitable: bool,
) -> str:
    if not spy_summary.exists and not csgp_summary.exists:
        return "Neither recent SPY nor recent CSGP file exists locally."
    if not spy_summary.exists:
        return "Recent CSGP exists locally, but recent SPY is still missing."
    if not csgp_summary.exists:
        return "Recent SPY exists locally, but recent CSGP is still missing."
    if suitable:
        return (
            f"Recent SPY and CSGP files overlap on {common_dates} trading date(s), "
            "so they look suitable for the future morning divergence study."
        )
    return (
        "Recent SPY and CSGP files both exist, but they do not overlap cleanly enough yet "
        "for the future morning divergence study."
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
