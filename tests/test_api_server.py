from pathlib import Path


def test_backend_api_does_not_expose_ai_audit_route():
    server_py = Path("backend/api/server.py").read_text(encoding="utf-8")

    assert "/api/audit" not in server_py
    assert "build_audit_fallback_response" not in server_py
    assert "weight_auditor" not in server_py
