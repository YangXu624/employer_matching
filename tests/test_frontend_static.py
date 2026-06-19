from pathlib import Path


def test_deployable_frontend_loads_config_before_app_script():
    index_html = Path("frontend/index.html").read_text(encoding="utf-8")

    config_index = index_html.index('src="/config.js"')
    app_index = index_html.index('src="/static/app.js"')

    assert config_index < app_index


def test_deployable_frontend_has_configured_backend_url():
    config_js = Path("frontend/config.js").read_text(encoding="utf-8")

    assert "window.EMPLOYER_MATCH_API_BASE_URL" in config_js
    assert "https://hardship-suing-slaw.ngrok-free.dev" in config_js


def test_deployable_frontend_uses_configured_api_base_for_backend_calls():
    app_js = Path("frontend/static/app.js").read_text(encoding="utf-8")

    assert "window.EMPLOYER_MATCH_API_BASE_URL" in app_js
    assert "function apiUrl(path)" in app_js
    assert 'apiUrl("/api/score")' in app_js
    assert 'apiUrl("/api/match")' in app_js


def test_frontend_shells_expose_ai_audit_controls():
    for path in ["frontend/index.html", "employer_match/static/index.html"]:
        html = Path(path).read_text(encoding="utf-8")

        assert 'id="auditButton"' in html
        assert 'id="auditSection"' in html
        assert 'id="auditResults"' in html
        assert 'id="applyAuditButton"' in html


def test_frontend_apps_call_unified_audit_endpoint_and_explain_fallback():
    for path in ["frontend/static/app.js", "employer_match/static/app.js"]:
        app_js = Path(path).read_text(encoding="utf-8")

        assert 'apiUrl("/api/audit")' in app_js or 'fetch("/api/audit"' in app_js
        assert "AI audit unavailable" in app_js
        assert "baseline weights were kept" in app_js
        assert "applyAuditResult" in app_js


def test_frontend_shells_expose_saved_check_cleanup_control():
    for path in ["frontend/index.html", "employer_match/static/index.html"]:
        html = Path(path).read_text(encoding="utf-8")

        assert 'id="clearHistoryButton"' in html
        assert 'class="section-header"' in html


def test_frontend_apps_support_deleting_and_clearing_saved_checks():
    for path in ["frontend/static/app.js", "employer_match/static/app.js"]:
        app_js = Path(path).read_text(encoding="utf-8")

        assert "deleteHistoryItem" in app_js
        assert "clearHistory" in app_js
        assert "delete-history-btn" in app_js
        assert 'localStorage.removeItem("employerMatchHistory")' in app_js


def test_frontend_apps_render_match_explanations():
    for path in ["frontend/static/app.js", "employer_match/static/app.js"]:
        app_js = Path(path).read_text(encoding="utf-8")

        assert "renderMatchExplanation" in app_js
        assert "Strongest alignment" in app_js
        assert "Watch gaps" in app_js
        assert "match.match_reason" in app_js


def test_frontend_audit_copy_distinguishes_ai_fallback():
    app_js = Path("frontend/static/app.js").read_text(encoding="utf-8")

    assert 'payload.audit_status?.startsWith("fallback_")' in app_js
    assert "AI audit unavailable" in app_js
    assert "baseline weights were kept" in app_js


def test_local_app_uses_local_api_by_default():
    app_js = Path("employer_match/static/app.js").read_text(encoding="utf-8")

    assert 'const API_BASE_URL = "";' in app_js
    assert "ngrok-free.app" not in app_js
