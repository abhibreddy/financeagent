# tests/test_ground_truth.py
# Regression guard for the hallucination fix: the ground-truth verifier must PASS a correct
# data summary and CATCH fabricated values. Deterministic — no LLM/network needed.
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.finance.agent import _direct_account_investigation, _verify_data_summary

ACC = "ACC-00009"


def test_verifier_passes_correct_summary():
    """A summary built straight from the tools must verify clean."""
    summary = _direct_account_investigation(ACC)
    result = _verify_data_summary(summary)
    assert "GROUND TRUTH VERIFIED" in result
    assert "DISCREPANCIES" not in result


def test_verifier_catches_hallucinated_values():
    """Tampered numbers must be flagged as discrepancies (the hallucination guard)."""
    summary = _direct_account_investigation(ACC)
    # Pull the real risk score out of the summary, then fabricate a wrong one.
    import re
    real = re.search(r"Risk Score:\s*(\d+)", summary).group(1)
    fake = "1" if real != "1" else "2"
    tampered = summary.replace(f"Risk Score: {real}", f"Risk Score: {fake}")

    result = _verify_data_summary(tampered)
    assert "DISCREPANCIES" in result
    assert "risk_score" in result
    assert "MISMATCH" in result
    # It must report the true value, not the fabricated one.
    assert f"actual {real}" in result
