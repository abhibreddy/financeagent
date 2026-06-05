# tests/test_invoice_agent.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_invoice_agent_imports():
    from invoice_agent import run_invoice_agent
    assert callable(run_invoice_agent)


def test_invoice_agent_returns_tuple():
    """Smoke test: run_invoice_agent returns (str, list) without Ollama running."""
    from unittest.mock import patch, MagicMock

    mock_response = MagicMock()
    mock_response.content = "Found 2 duplicate invoices."
    mock_response.tool_calls = []

    with patch("invoice_agent.ChatOllama") as mock_llm_class:
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        from invoice_agent import run_invoice_agent
        result = run_invoice_agent(
            messages=[{"role": "user", "content": "Check for duplicates"}],
            session_id="test-session",
            analyst="tester",
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        response_text, updated_msgs = result
        assert isinstance(response_text, str)
        assert isinstance(updated_msgs, list)
