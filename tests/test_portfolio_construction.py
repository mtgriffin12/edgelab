from edgelab.portfolios.construction import ModelPortfolioEngine
from edgelab.portfolios.schema import PortfolioConstructionRequest, PortfolioStyle


def test_portfolio_construction_returns_sample_portfolios() -> None:
    result = ModelPortfolioEngine().construct()

    assert result.portfolio_count == 4
    assert {portfolio.portfolio_id for portfolio in result.portfolios} >= {
        "core-research-portfolio",
        "defensive-research-portfolio",
        "opportunistic-research-portfolio",
        "benchmark-comparison-portfolio",
    }


def test_portfolio_construction_includes_cash_allocation() -> None:
    result = ModelPortfolioEngine().construct()

    for portfolio in result.portfolios:
        assert portfolio.target_cash.target_weight_pct >= portfolio.risk_limits.min_cash_weight_pct
        assert portfolio.target_cash.target_value > 0


def test_portfolio_construction_respects_max_position_limits() -> None:
    result = ModelPortfolioEngine().construct()

    for portfolio in result.portfolios:
        for holding in portfolio.holdings:
            if holding.symbol in {"SPY", "QQQ"}:
                assert holding.target_weight_pct <= portfolio.risk_limits.max_etf_weight_pct
            else:
                assert (
                    holding.target_weight_pct <= portfolio.risk_limits.max_single_equity_weight_pct
                )


def test_portfolio_construction_returns_benchmark_comparison_portfolio() -> None:
    result = ModelPortfolioEngine().construct()
    benchmark = [p for p in result.portfolios if p.style == PortfolioStyle.BENCHMARK_COMPARISON]

    assert len(benchmark) == 1
    assert benchmark[0].status.value == "reference_only"


def test_portfolio_construction_can_filter_by_style() -> None:
    core = ModelPortfolioEngine().construct(
        PortfolioConstructionRequest(style=PortfolioStyle.CORE_RESEARCH)
    )

    assert core.portfolio_count == 1
    assert core.portfolios[0].style == PortfolioStyle.CORE_RESEARCH


def test_monitoring_notes_are_generated() -> None:
    portfolio = ModelPortfolioEngine().get_portfolio("core-research-portfolio")

    assert portfolio is not None
    assert portfolio.monitoring_notes
    assert any(note.symbol == "SPY" for note in portfolio.monitoring_notes)
