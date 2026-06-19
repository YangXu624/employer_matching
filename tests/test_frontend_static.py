from pathlib import Path


def test_deployable_frontend_loads_config_before_app_script():
    index_html = Path("frontend/index.html").read_text(encoding="utf-8")

    config_index = index_html.index('src="/config.js"')
    app_index = index_html.index('src="/static/app.js"')

    assert config_index < app_index


def test_deployable_frontend_has_no_committed_tunnel_url():
    config_js = Path("frontend/config.js").read_text(encoding="utf-8")

    assert 'window.EMPLOYER_MATCH_API_BASE_URL = "";' in config_js
    assert "ngrok" not in config_js


def test_deployable_frontend_uses_configured_api_base_for_backend_calls():
    app_js = Path("frontend/static/app.js").read_text(encoding="utf-8")

    assert "window.EMPLOYER_MATCH_API_BASE_URL" in app_js
    assert "function apiUrl(path)" in app_js
    assert 'apiUrl("/api/score")' in app_js
    assert 'apiUrl("/api/match")' in app_js
