from pathlib import Path


def test_backend_api_does_not_expose_ai_audit_route():
    server_py = Path("backend/api/server.py").read_text(encoding="utf-8")

    assert "/api/audit" not in server_py
    assert "build_audit_fallback_response" not in server_py
    assert "weight_auditor" not in server_py


def test_backend_api_has_llm_score_route():
    server_py = Path("backend/api/server.py").read_text(encoding="utf-8")

    assert "/api/llm-score" in server_py
    assert "llm_score_text_payload" in server_py


def test_backend_api_has_jobs_routes():
    server_py = Path("backend/api/server.py").read_text(encoding="utf-8")

    assert "/api/jobs" in server_py
    assert "handle_create_job" in server_py
    assert "handle_list_jobs" in server_py
    assert "handle_get_job" in server_py
    # Backend must reach Supabase only through the repository factory.
    assert "get_job_store" in server_py
    assert "supabase" not in server_py.lower()
