from pathlib import Path


def test_frontend_audit_copy_distinguishes_ai_fallback():
    app_js = Path("frontend/static/app.js").read_text(encoding="utf-8")

    assert 'payload.audit_status?.startsWith("fallback_")' in app_js
    assert "AI audit unavailable" in app_js
    assert "baseline weights were kept" in app_js


def test_local_app_uses_local_api_by_default():
    app_js = Path("employer_match/static/app.js").read_text(encoding="utf-8")

    assert 'const API_BASE_URL = "";' in app_js
    assert "ngrok-free.app" not in app_js
