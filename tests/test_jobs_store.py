import pytest

from backend.db.jobs import (
    JobValidationError,
    build_competencies,
    normalize_status,
    validate_weights,
)
from backend.db.sqlite_jobs import SqliteJobStore
from employer_match.rubric_store import COMPETENCY_ORDER


def even_weights() -> dict[str, float]:
    weights = {cid: 12 for cid in COMPETENCY_ORDER}
    weights[COMPETENCY_ORDER[0]] = 16  # 7*12 + 16 = 100
    return weights


def test_validate_weights_accepts_sum_near_100():
    cleaned = validate_weights(even_weights())
    assert round(sum(cleaned.values())) == 100
    assert set(cleaned) == set(COMPETENCY_ORDER)


def test_validate_weights_rejects_missing_keys():
    with pytest.raises(JobValidationError):
        validate_weights({"technology": 100})


def test_validate_weights_rejects_bad_sum():
    weights = {cid: 1 for cid in COMPETENCY_ORDER}
    with pytest.raises(JobValidationError):
        validate_weights(weights)


def test_normalize_status_rejects_unknown():
    assert normalize_status("Published") == "published"
    with pytest.raises(JobValidationError):
        normalize_status("pending")


def test_build_competencies_includes_label_and_description():
    weights = even_weights()
    score = {"competencies": [{"competency_id": "technology", "matched_level": 4}]}
    rows = build_competencies(weights, score)

    assert [row["competency_id"] for row in rows] == list(COMPETENCY_ORDER)
    tech = next(row for row in rows if row["competency_id"] == "technology")
    assert tech["label"] == "Technology"
    assert tech["description"]  # rubric definition copied in
    assert tech["weight"] == weights["technology"]
    assert tech["matched_level"] == 4


def test_sqlite_store_create_list_get_roundtrip(tmp_path):
    store = SqliteJobStore(tmp_path / "jobs.db")
    job = store.create_job(
        title="Data Platform Engineer",
        jd_text="Build pipelines.",
        weights=even_weights(),
        score={"overall_score": 87, "competencies": [{"competency_id": "technology", "matched_level": 5}]},
    )

    assert job["id"]
    assert job["status"] == "published"
    assert job["competencies"][-1]["competency_id"] == "technology"

    listed = store.list_jobs()
    assert [j["id"] for j in listed] == [job["id"]]

    fetched = store.get_job(job["id"])
    assert fetched["title"] == "Data Platform Engineer"

    with pytest.raises(KeyError):
        store.get_job("does-not-exist")


def test_sqlite_store_rejects_empty_jd(tmp_path):
    store = SqliteJobStore(tmp_path / "jobs.db")
    with pytest.raises(JobValidationError):
        store.create_job(title="x", jd_text="   ", weights=even_weights())


def test_sqlite_store_status_filter(tmp_path):
    store = SqliteJobStore(tmp_path / "jobs.db")
    store.create_job(title="draft job", jd_text="text", weights=even_weights(), status="draft")
    store.create_job(title="pub job", jd_text="text", weights=even_weights(), status="published")

    published = store.list_jobs(status="published")
    assert [j["title"] for j in published] == ["pub job"]

    everything = store.list_jobs(status=None)
    assert len(everything) == 2
