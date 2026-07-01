# tests/test_trading.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_trading_utils_import():
    from modules.trading import utils
    assert callable(utils.load_positions)


def test_portfolio_metrics():
    from modules.trading import utils
    pos = utils.load_positions()
    m = utils.compute_portfolio_metrics(pos)
    assert m["total_market_value"] > 0
    assert m["num_positions"] == len(pos)
    assert isinstance(m["weights"], dict)


def test_exposure_and_risk():
    from modules.trading import utils
    pos, prices = utils.load_positions(), utils.load_prices()
    exp = utils.compute_exposure(pos)
    assert exp["concentration_level"] in {"High", "Medium", "Low"}
    assert 0 <= exp["largest_weight_pct"] <= 100

    risk = utils.compute_risk_metrics(prices, pos)
    assert 0 <= risk["risk_score"] <= 100
    assert risk["risk_level"] in {"High", "Medium", "Low"}


def test_signal_and_sentiment_stubs():
    from modules.trading import utils
    prices = utils.load_prices()
    sig = utils.signal_stub("AAPL", prices)
    assert sig["signal"] in {"BUY", "HOLD", "SELL", "UNKNOWN"}
    sent = utils.sentiment_stub("NVDA")
    assert -1.0 <= sent["sentiment_score"] <= 1.0
    assert sent["source"] == "synthetic"


def test_run_trading_agent_returns_tuple():
    """Smoke test: run_trading_agent returns (str, list, dict) with a mocked LLM."""
    from unittest.mock import patch, MagicMock
    mock_response = MagicMock()
    mock_response.content = "Portfolio is concentrated in Technology."

    with patch("core.llm.AzureChatOpenAI") as mock_llm_class:
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        from modules.trading.trading_agent import run_trading_agent
        result = run_trading_agent(
            messages=[{"role": "user", "content": "Analyze portfolio risk"}],
            session_id="test-trading",
            analyst="tester",
        )
        assert isinstance(result, tuple) and len(result) == 3
        text, msgs, debug = result
        assert isinstance(text, str) and isinstance(msgs, list) and isinstance(debug, dict)
        # Data stage is deterministic — ground truth must be present
        assert "GROUND TRUTH" in debug.get("ground_truth", "")


def test_forecaster_requires_key(monkeypatch):
    """build_forecast_prompt should fail clearly when no Finnhub key is configured."""
    import core.config as cfg
    from modules.trading import forecaster
    monkeypatch.setattr(cfg, "FINNHUB_API_KEY", "")
    monkeypatch.setattr(forecaster, "FINNHUB_API_KEY", "")
    import pytest
    with pytest.raises(forecaster.ForecasterError):
        forecaster.build_forecast_prompt("AAPL", "2026-06-01", weeks=1)
