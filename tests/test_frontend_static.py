from pathlib import Path


def test_frontend_audit_copy_distinguishes_ai_fallback():
    app_js = Path("frontend/static/app.js").read_text(encoding="utf-8")

    assert 'payload.audit_status?.startsWith("fallback_")' in app_js
    assert "AI audit unavailable" in app_js
    assert "baseline weights were kept" in app_js
