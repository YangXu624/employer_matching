from backend.api.server import build_audit_fallback_response
from employer_match.rubric_store import COMPETENCY_ORDER


def test_build_audit_fallback_response_returns_baseline_without_changes():
    weights = {competency_id: index * 10 for index, competency_id in enumerate(COMPETENCY_ORDER)}

    payload = build_audit_fallback_response(
        weights=weights,
        status="fallback_missing_api_key",
        message="GOOGLE_API_KEY is not set.",
    )

    assert payload["audit_status"] == "fallback_missing_api_key"
    assert payload["changes_count"] == 0
    assert payload["corrected"] == weights
    assert payload["warning"] == "GOOGLE_API_KEY is not set."
    assert "baseline weights were kept" in payload["summary"]
    assert [item["competency_id"] for item in payload["competencies"]] == COMPETENCY_ORDER
    assert all(item["changed"] is False for item in payload["competencies"])
    assert all(item["delta"] == 0 for item in payload["competencies"])
