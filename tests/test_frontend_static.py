from pathlib import Path


def test_deployable_frontend_loads_config_before_app_script():
    index_html = Path("frontend/index.html").read_text(encoding="utf-8")

    config_index = index_html.index('src="/config.js"')
    app_index = index_html.index('src="/static/app.js"')

    assert config_index < app_index


def test_deployable_frontend_has_configured_backend_url():
    config_js = Path("frontend/config.js").read_text(encoding="utf-8")

    assert "window.EMPLOYER_MATCH_API_BASE_URL" in config_js


def test_deployable_frontend_uses_configured_api_base_for_backend_calls():
    app_js = Path("frontend/static/app.js").read_text(encoding="utf-8")

    assert "window.EMPLOYER_MATCH_API_BASE_URL" in app_js
    assert "function apiUrl(path)" in app_js
    assert 'apiUrl("/api/score")' in app_js
    assert 'apiUrl("/api/match")' in app_js


def test_frontend_index_does_not_expose_ai_audit_controls():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "AI Audit" not in html
    assert 'id="auditButton"' not in html
    assert 'id="auditSection"' not in html
    assert 'id="auditResults"' not in html
    assert 'id="applyAuditButton"' not in html


def test_frontend_app_does_not_call_or_render_ai_audit():
    app_js = Path("frontend/static/app.js").read_text(encoding="utf-8")

    assert "/api/audit" not in app_js
    assert "auditButton" not in app_js
    assert "renderAudit" not in app_js
    assert "applyAuditResult" not in app_js


def test_frontend_index_exposes_saved_check_cleanup_control():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert 'id="clearHistoryButton"' in html
    assert 'class="section-header"' in html


def test_frontend_app_supports_deleting_and_clearing_saved_checks():
    app_js = Path("frontend/static/app.js").read_text(encoding="utf-8")

    assert "deleteHistoryItem" in app_js
    assert "clearHistory" in app_js
    assert "delete-history-btn" in app_js
    assert 'localStorage.removeItem("employerMatchHistory")' in app_js


def test_frontend_app_renders_match_explanations():
    app_js = Path("frontend/static/app.js").read_text(encoding="utf-8")

    assert "renderMatchExplanation" in app_js
    assert "Strongest alignment" in app_js
    assert "Watch gaps" in app_js
    assert "match.match_reason" in app_js


def test_frontend_static_assets_do_not_include_audit_copy():
    app_js = Path("frontend/static/app.js").read_text(encoding="utf-8")

    assert "audit_status" not in app_js
    assert "AI audit unavailable" not in app_js
    assert "baseline weights were kept" not in app_js
