"""Offline regressions for reference manifests, audit metadata, and monitoring."""
import asyncio
import hashlib
import importlib.util
import io
import json
import socket
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException, Request
from PIL import Image
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from test_api_regressions import diagnosis, frame, password_hash, runtime
from app.core.config import settings
from app.db import models
from app.routers import admin, prediction, webcam
from app.services import ai
from app.services.auth import create_access_token, verify_admin
from app.services.webcam import AlertConsensusTracker


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = (
    "2f64de060dd9_create_initial_tables.py",
    "8766043b40ed_align_database_with_current_models.py",
    "a11e7c4d9f20_add_webcam_alerts.py",
    "c37f8e92a411_add_reference_sources.py",
    "d42a91c8e510_preserve_diagnosis_audit.py",
)
AUDIT_COLUMNS = {
    "requires_review", "grounding_source", "reference_source",
    "reference_url", "reference_record_id",
}


@pytest.fixture(autouse=True)
def no_external_io(monkeypatch):
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("This regression suite must not make network requests")

    # TestClient uses its own transport; ordinary HTTP, DNS, DB and mail fail closed.
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    monkeypatch.setattr(ai, "client", SimpleNamespace(models=SimpleNamespace(generate_content=forbidden)))
    yield
    assert not attempts, "A production exception handler swallowed a network attempt"


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def rag_modules(tmp_path, monkeypatch):
    from google import genai

    def embed(*, model, contents, config):
        assert model == "gemini-embedding-001"
        assert config.output_dimensionality == 3
        texts = contents if isinstance(contents, list) else [contents]
        return SimpleNamespace(embeddings=[
            SimpleNamespace(values=[0.0, 4.0, 0.0] if "Mite" in text else [3.0, 0.0, 0.0])
            for text in texts
        ])

    embedding = Mock(side_effect=embed)
    client = SimpleNamespace(models=SimpleNamespace(embed_content=embedding))
    monkeypatch.setattr(genai, "Client", lambda **kwargs: client)
    fake_rag = ModuleType("app.services.rag")
    fake_rag.search_knowledge_base = lambda *args, **kwargs: ""
    monkeypatch.setitem(sys.modules, "app.services.rag", fake_rag)
    rag = _load_module("_regression_real_rag", ROOT / "app/services/rag.py")
    builder = _load_module("_regression_real_rag_builder", ROOT / "build_knowledge_base.py")
    assert rag is not fake_rag and sys.modules["app.services.rag"] is fake_rag
    assert Path(rag.__file__).resolve() == (ROOT / "app/services/rag.py").resolve()

    source = tmp_path / "references.json"
    disease = dict(crop_name="Tomato", disease_name="Spot", description="Leaf spots",
                   treatment="Inspect affected leaves", source_name="Disease reference",
                   source_url="https://example.invalid/disease", source_record_id="disease-1")
    pest = dict(crop_name="Tomato", pest_name="Mite", description="Leaf damage",
                treatment="Inspect leaf undersides", source_name="Pest reference",
                source_url="https://example.invalid/pest", source_record_id="pest-1")
    incomplete = [dict(disease, **{field: " "}) for field in disease]
    source.write_text(json.dumps({"diseases": [disease, *incomplete], "pests": [pest]}), encoding="utf-8")
    index_path, content_path = tmp_path / "index.faiss", tmp_path / "content.json"
    for module in (rag, builder):
        monkeypatch.setattr(module, "EMBEDDING_DIMENSION", 3)
        monkeypatch.setattr(module, "FAISS_INDEX_PATH", index_path)
        monkeypatch.setattr(module, "CONTENT_PATH", content_path)
    monkeypatch.setattr(builder, "REFERENCE_PATH", source)
    monkeypatch.setattr(builder, "EMBEDDING_BATCH_SIZE", 1)
    return SimpleNamespace(rag=rag, builder=builder, embedding=embedding, source=source,
                           index_path=index_path, content_path=content_path)


def _build(rag_modules):
    entries = rag_modules.builder.load_documents()
    rag_modules.builder.build_and_save_knowledge_base(entries)
    return entries


def test_rag_build_load_search_round_trip_with_real_faiss(rag_modules):
    r = rag_modules
    entries = _build(r)
    assert [entry["source_record_id"] for entry in entries] == ["disease-1", "pest-1"]
    manifest = json.loads(r.content_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 2 and manifest["dimension"] == 3
    assert manifest["embedding_model"] == r.rag.EMBEDDING_MODEL
    assert manifest["source_file"] == r.source.name
    assert manifest["source_sha256"] == hashlib.sha256(r.source.read_bytes()).hexdigest()
    assert manifest["index_sha256"] == hashlib.sha256(r.index_path.read_bytes()).hexdigest()
    assert datetime.fromisoformat(manifest["built_at"]).utcoffset() == timedelta(0)
    assert manifest["entries"] == entries
    assert r.embedding.call_count == 2
    for call, entry in zip(r.embedding.call_args_list, entries):
        assert call.kwargs["contents"] == [entry["text"]]
        assert call.kwargs["config"].task_type == "RETRIEVAL_DOCUMENT"
    r.rag.load_knowledge_base()
    assert r.rag.faiss_index.ntotal == 2 and r.rag.faiss_index.d == 3
    assert r.rag.faiss_index.metric_type == r.rag.faiss.METRIC_INNER_PRODUCT
    assert r.rag.faiss_index.reconstruct(0).tolist() == pytest.approx([1, 0, 0])
    assert r.rag.faiss_index.reconstruct(1).tolist() == pytest.approx([0, 1, 0])
    assert r.rag.knowledge_content == [entry["text"] for entry in entries]
    assert r.rag.search_knowledge_base("Mite", k=1) == entries[1]["text"]
    assert r.embedding.call_args.kwargs["config"].task_type == "RETRIEVAL_QUERY"
    assert r.rag.search_knowledge_base("Spot", k=99) == "\n\n".join(e["text"] for e in entries)
    assert not list(r.index_path.parent.glob("*.tmp"))


@pytest.mark.parametrize("corruption", [
    "legacy_list", "old_schema", "hash", "model", "dimension", "count", "source", "missing_index",
    "index_metric", "index_dimension",
])
def test_rag_rejects_invalid_manifest_and_clears_loaded_state(rag_modules, corruption):
    r = rag_modules
    _build(r)
    r.rag.load_knowledge_base()
    assert r.rag.faiss_index is not None and r.rag.knowledge_content
    manifest = json.loads(r.content_path.read_text(encoding="utf-8"))
    if corruption == "legacy_list":
        manifest = [entry["text"] for entry in manifest["entries"]]
    elif corruption == "source":
        manifest["entries"][0].pop("source_record_id")
    elif corruption == "count":
        manifest["entries"].pop()
    elif corruption == "missing_index":
        r.index_path.unlink()
    elif corruption in {"index_metric", "index_dimension"}:
        dimension = 4 if corruption == "index_dimension" else 3
        factory = r.rag.faiss.IndexFlatL2 if corruption == "index_metric" else r.rag.faiss.IndexFlatIP
        incompatible = factory(dimension)
        incompatible.add(r.rag.np.ones((2, dimension), dtype=r.rag.np.float32))
        r.rag.faiss.write_index(incompatible, str(r.index_path))
        manifest["index_sha256"] = hashlib.sha256(r.index_path.read_bytes()).hexdigest()
    else:
        key, value = {"old_schema": ("schema_version", 1), "hash": ("index_sha256", "0" * 64),
                      "model": ("embedding_model", "obsolete"), "dimension": ("dimension", 4)}[corruption]
        manifest[key] = value
    r.content_path.write_text(json.dumps(manifest), encoding="utf-8")
    r.embedding.reset_mock()
    r.rag.load_knowledge_base()
    assert r.rag.faiss_index is None and r.rag.knowledge_content == []
    assert r.rag.search_knowledge_base("Spot") == ""
    r.embedding.assert_not_called()


@pytest.mark.parametrize("failure", ["empty", "wrong_dimension", "nonfinite"])
def test_rag_failed_rebuild_preserves_existing_pair(rag_modules, failure):
    r = rag_modules
    entries = _build(r)
    previous = r.index_path.read_bytes(), r.content_path.read_bytes()
    r.embedding.reset_mock()
    if failure == "empty":
        entries = []
    else:
        values = [1.0, 0.0] if failure == "wrong_dimension" else [float("nan"), 0.0, 0.0]
        r.embedding.side_effect = lambda **kwargs: SimpleNamespace(embeddings=[SimpleNamespace(values=values)])
    with pytest.raises(ValueError if failure == "empty" else RuntimeError,
                       match="No traceable|Embedding dimensions"):
        r.builder.build_and_save_knowledge_base(entries)
    if failure == "empty":
        r.embedding.assert_not_called()
    assert (r.index_path.read_bytes(), r.content_path.read_bytes()) == previous
    assert not list(r.index_path.parent.glob("*.tmp"))
    r.rag.load_knowledge_base()
    assert r.rag.faiss_index.ntotal == 2


@pytest.mark.parametrize("path", ["/api/v1/predict/", "/api/v1/webcam/analyze"])
@pytest.mark.parametrize("case,status", [("invalid_mime", 400), ("mismatch", 400),
                                        ("empty", 400), ("blank", 422), ("oversize", 413)])
def test_image_rejections_do_not_call_ai_or_leave_files(runtime, monkeypatch, path, case, status):
    content, mime = frame(), "image/jpeg"
    monkeypatch.setattr(settings, "WEBCAM_MAX_IMAGE_BYTES", len(content) + 1024)
    monkeypatch.setattr(settings, "WEBCAM_MIN_IMAGE_WIDTH", 320)
    monkeypatch.setattr(settings, "WEBCAM_MIN_IMAGE_HEIGHT", 240)
    if case == "invalid_mime":
        mime = "application/octet-stream"
    elif case == "mismatch":
        mime = "image/png"
    elif case == "empty":
        content = b""
    elif case == "blank":
        buffer = io.BytesIO()
        Image.new("RGB", (640, 480), "gray").save(buffer, format="JPEG")
        content = buffer.getvalue()
    else:
        monkeypatch.setattr(settings, "WEBCAM_MAX_IMAGE_BYTES", len(content) - 1)
    model_call = Mock(side_effect=AssertionError("Rejected images must not reach AI"))
    monkeypatch.setattr(prediction, "diagnostic_plant", model_call)
    monkeypatch.setattr(webcam, "diagnostic_plant", model_call)
    response = runtime["client"].post(path, headers=runtime["headers"][1],
                                      files={"file": ("leaf.jpg", content, mime)})
    assert response.status_code == status, response.text
    assert response.json()["detail"]
    model_call.assert_not_called()
    assert prediction.prediction_cache == {}
    assert not list(runtime["temporary"].iterdir()) and not list(runtime["uploads"].iterdir())
    assert runtime["db"].query(models.PlantDiary).count() == 0
    assert runtime["db"].query(models.WebcamAlert).count() == 0


@pytest.mark.parametrize("category,record_type,name_field,id_field", [
    ("disease", models.Disease, "disease_name", "disease_id"),
    ("pest", models.Pest, "pest_name", "pest_id"),
])
def test_grounding_unknown_and_cross_crop_use_real_sql(runtime, category, record_type, name_field, id_field):
    db = runtime["db"]
    db.add(models.Crop(crop_id=2, crop_name="Other crop"))
    db.add(record_type(**{id_field: 20, name_field: "Other-only status"}, crop_id=2,
                       description="Other symptoms", treatment="Other advice", source_name="Other source",
                       source_url="https://example.invalid/other", source_record_id="other-20"))
    db.commit()
    candidate = dict(diagnosis(), category=category, status_name="Other-only status")
    for overrides in ({}, {"status_name": "Not in database"}, {"crop_name": "Invented crop"},
                      {"category": "unknown"}):
        result = ai.ground_diagnosis_in_database(dict(candidate, **overrides), db)
        assert result["category"] == "unknown" and result["requires_review"] is True
        assert result["status_name"] == ai.UNKNOWN_STATUS_NAME
        assert result["grounding_source"] == "safety_fallback" and result["confidence"] <= 0.5
        assert not result.get("reference_record_id")
        assert result["treatment"] not in {candidate["treatment"], "Other advice"}
    grounded = ai.ground_diagnosis_in_database(dict(candidate, crop_name="Other crop"), db)
    assert grounded["category"] == category and grounded["requires_review"] is False
    assert grounded["reference_record_id"] == "other-20" and grounded["treatment"] == "Other advice"
    db.get(record_type, 20).source_url = None
    db.commit()
    assert ai.ground_diagnosis_in_database(dict(candidate, crop_name="Other crop"), db)["requires_review"] is True


def test_admin_helpers_use_database_role_not_username_or_token_claim(runtime):
    db = runtime["db"]
    administrator, owner = db.get(models.User, 4), db.get(models.User, 1)
    assert asyncio.run(verify_admin(administrator)) is administrator
    with pytest.raises(HTTPException) as denied:
        asyncio.run(verify_admin(owner))
    assert denied.value.status_code == 403

    def authorize(user_id, **claims):
        token = create_access_token({"user_id": user_id, "role": "admin", **claims})
        request = Request({"type": "http", "method": "GET", "path": "/admin/users/", "scheme": "http",
                           "server": ("testserver", 80), "query_string": b"",
                           "headers": [(b"authorization", ("Bearer " + token).encode())]})
        return asyncio.run(admin.require_admin(request, db=db))

    assert authorize(4) is administrator
    with pytest.raises(HTTPException) as forged_role:
        authorize(1, sub="administrator")
    assert forged_role.value.status_code == 403
    administrator.role = "user"
    db.commit()
    with pytest.raises(HTTPException) as revoked:
        authorize(4)
    assert revoked.value.status_code == 403
    owner.role = "admin"
    db.commit()
    assert authorize(1) is owner
    owner.is_email_verified = False
    db.commit()
    with pytest.raises(HTTPException) as unverified:
        authorize(1)
    assert unverified.value.status_code == 403


def _confirmed_diary(runtime, monkeypatch):
    monkeypatch.setattr(prediction, "diagnostic_plant", lambda *args: diagnosis())
    client, headers = runtime["client"], runtime["headers"][1]
    result = client.post("/api/v1/predict/", headers=headers,
                         files={"file": ("leaf.jpg", frame(), "image/jpeg")})
    assert result.status_code == 200, result.text
    saved = client.post("/api/v1/diaries/confirm/" + result.json()["prediction_id"], headers=headers, json={})
    assert saved.status_code == 201, saved.text
    return runtime["db"].get(models.PlantDiary, saved.json()["data"]["id"])


def _diary_snapshot(entry):
    fields = ("crop_id", "disease_id", "pest_id", "status_name", "category", "confidence", "requires_review",
              "grounding_source", "reference_source", "reference_url", "reference_record_id",
              "gemini_suggestion", "gemini_treatment")
    return {field: getattr(entry, field) for field in fields}


def test_diary_user_edits_revalidate_crop_and_clear_model_confidence(runtime, monkeypatch):
    entry = _confirmed_diary(runtime, monkeypatch)
    db, client = runtime["db"], runtime["client"]
    db.add(models.Crop(crop_id=2, crop_name="Other crop"))
    db.add(models.Pest(pest_id=2, crop_id=2, pest_name="Other pest", description="Pest symptoms",
                       treatment="Pest advice", source_name="Pest source", source_url="https://example.invalid/pest",
                       source_record_id="pest-2"))
    db.commit()
    before = _diary_snapshot(entry)
    path = f"/api/v1/diaries/{entry.id}"
    for payload in ({"crop_name": "Missing crop"}, {"crop_name": "Other crop"}, {"status_name": "Other pest"}):
        response = client.patch(path, headers=runtime["headers"][1], json=payload)
        assert response.status_code == 400, response.text
        db.refresh(entry)
        assert _diary_snapshot(entry) == before
    replacement = {"crop_name": "Other crop", "status_name": "Other pest"}
    assert client.patch(path, headers=runtime["headers"][2], json=replacement).status_code == 404
    response = client.patch(path, headers=runtime["headers"][1], json=replacement)
    assert response.status_code == 200, response.text
    db.refresh(entry)
    assert (entry.crop_id, entry.pest_id, entry.disease_id, entry.category) == (2, 2, None, "pest")
    assert entry.confidence is None and entry.requires_review is True
    assert entry.grounding_source == "user_edited_database_match"
    assert (entry.reference_source, entry.reference_url, entry.reference_record_id) == (
        "Pest source", "https://example.invalid/pest", "pest-2")
    assert (entry.gemini_suggestion, entry.gemini_treatment) == ("Pest symptoms", "Pest advice")
    assert db.query(models.Crop).count() == 2 and db.query(models.Pest).count() == 1


def test_diary_personal_annotation_retains_original_source_snapshot(runtime, monkeypatch):
    entry = _confirmed_diary(runtime, monkeypatch)
    db = runtime["db"]
    before = _diary_snapshot(entry)
    assert before["reference_record_id"] == "test-only" and before["requires_review"] is False
    reference = db.get(models.Disease, 1)
    reference.source_name, reference.source_url, reference.source_record_id = "Revised", "https://example.invalid/new", "new"
    reference.description, reference.treatment = "Revised symptoms", "Revised advice"
    db.commit()
    response = runtime["client"].patch(f"/api/v1/diaries/{entry.id}", headers=runtime["headers"][1],
                                       json={"user_corrected_status": "My personal observation", "user_note": "Check tomorrow"})
    assert response.status_code == 200, response.text
    db.refresh(entry)
    assert (entry.user_corrected_status, entry.user_note) == ("My personal observation", "Check tomorrow")
    assert _diary_snapshot(entry) == before


def test_webcam_interleaved_regions_600_second_scans_gap_and_cooldown(monkeypatch):
    for key, value in {"WEBCAM_SAMPLE_INTERVAL_SECONDS": 600, "WEBCAM_ALERT_CONFIDENCE": 0.8,
                       "WEBCAM_ALERT_CONSECUTIVE_MATCHES": 3, "WEBCAM_ALERT_COOLDOWN_SECONDS": 2400}.items():
        monkeypatch.setattr(settings, key, value)
    tracker = AlertConsensusTracker()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    anomaly = dict(diagnosis(), grounding_source="disease_database", requires_review=False)

    def scan(second, region="left", user=1, session="camera-a", result=None):
        return tracker.evaluate(user, anomaly if result is None else result, start + timedelta(seconds=second),
                                session_id=session, region_id=region)

    for number, second in enumerate((0, 600, 1200), 1):
        for region, offset in (("left", 0), ("right", 5)):
            result = scan(second + offset, region)
            assert result["streak"] == number and result["triggered"] is (number == 3)
    assert scan(1210, session="camera-b")["streak"] == 1
    assert scan(1211, user=2)["streak"] == 1
    for second in (1800, 2400, 3000, 3599):
        result = scan(second)
        assert result["reason"] == "cooldown" and result["triggered"] is False
    assert scan(3600)["triggered"] is True
    right = scan(3601, "right")
    assert right["streak"] == 1 and right["reason"] == "cooldown" and right["triggered"] is False
    assert scan(4201, "right")["streak"] == 2
    assert scan(4801, "right")["triggered"] is True
    # Exactly three scan intervals remain contiguous; one second beyond resets.
    at_boundary = scan(5400)
    assert at_boundary["streak"] > 1 and at_boundary["reason"] == "cooldown"
    beyond_boundary = scan(7201)
    assert beyond_boundary["streak"] == 1 and beyond_boundary["triggered"] is False
    assert scan(7801)["streak"] == 2
    assert scan(8401)["triggered"] is True
    unknown = scan(8402, result=dict(anomaly, category="unknown", requires_review=True))
    assert unknown["streak"] == 0 and unknown["reason"] == "not_a_grounded_anomaly"


def _migrations():
    return [_load_module("_regression_migration_" + name[:12], ROOT / "alembic/versions" / name)
            for name in MIGRATIONS]


def test_migration_sqlite_preserves_rows_and_defaults_to_review():
    migrations = _migrations()
    engine = sa.create_engine("sqlite://")
    try:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                for migration in migrations[:-1]:
                    migration.upgrade()
                # Initial migrations use MySQL's now(); seed explicit timestamps on SQLite.
                conn.execute(sa.text("INSERT INTO user (user_id, username, password_hash, is_email_verified, email_verified_at, created_at) "
                                     "VALUES (1, 'pending', 'hash', 0, '2026-01-01', '2026-01-01'), "
                                     "(2, 'verified', 'hash', 1, '2026-01-02', '2026-01-01')"))
                conn.execute(sa.text("INSERT INTO plant_diary (id, user_id, status_name, suggestion, created_at) "
                                     "VALUES (1, 1, 'legacy', 'keep', '2026-01-01')"))
                conn.execute(sa.text("INSERT INTO webcam_alert (id, user_id, category, status_name, confidence, "
                                     "consecutive_matches, image_url) VALUES (1, 1, 'disease', 'legacy', 0.95, 3, 'keep.jpg')"))
                migrations[-1].upgrade()
            inspector = sa.inspect(conn)
            for table_name in ("user", "disease", "pests", "plant_diary", "webcam_alert"):
                columns = {column["name"]: column for column in inspector.get_columns(table_name)}
                expected = models.Base.metadata.tables[table_name].columns
                assert set(columns) == set(expected.keys())
                for name in columns:
                    assert columns[name]["nullable"] == expected[name].nullable, (table_name, name)
                    assert columns[name]["type"]._type_affinity is expected[name].type._type_affinity
                    assert getattr(columns[name]["type"], "length", None) == getattr(expected[name].type, "length", None)
            pending, verified = conn.execute(sa.text("SELECT email_verified_at FROM user ORDER BY user_id")).scalars().all()
            assert pending is None and str(verified).startswith("2026-01-02")
            for table in ("plant_diary", "webcam_alert"):
                row = conn.execute(sa.text(f"SELECT * FROM {table} WHERE id = 1")).mappings().one()
                assert row["requires_review"] == 1 and row["grounding_source"] == "legacy_unverified"
                assert all(row[name] is None for name in ("reference_source", "reference_url", "reference_record_id"))
                assert row["status_name"] == "legacy"
                if table == "plant_diary":
                    assert row["category"] == "unknown" and row["suggestion"] == "keep"
                else:
                    assert (row["session_id"], row["region_id"], row["image_url"]) == ("legacy", "full-frame", "keep.jpg")
            with Operations.context(MigrationContext.configure(conn)):
                migrations[-1].downgrade()
            for table in ("plant_diary", "webcam_alert"):
                assert not AUDIT_COLUMNS.intersection(column["name"] for column in sa.inspect(conn).get_columns(table))
                assert conn.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one() == 1
            assert conn.execute(sa.text("SELECT email_verified_at FROM user WHERE user_id = 1")).scalar_one() is None
    finally:
        engine.dispose()


def test_migrations_and_metadata_compile_for_mysql_without_connection():
    output = io.StringIO()
    context = MigrationContext.configure(dialect_name="mysql", opts={"as_sql": True, "output_buffer": output})
    previous = None
    with Operations.context(context):
        for migration in _migrations():
            assert migration.down_revision == previous
            migration.upgrade()
            previous = migration.revision
    statements = [" ".join(statement.replace("`", "").split()) for statement in output.getvalue().split(";")]
    assert any(statement in {
        "ALTER TABLE user MODIFY email_verified_at DATETIME NULL",
        "ALTER TABLE user CHANGE email_verified_at email_verified_at DATETIME NULL",
    } for statement in statements)
    assert "UPDATE user SET email_verified_at = NULL WHERE is_email_verified = false" in statements
    for table_name in ("disease", "pests", "plant_diary", "webcam_alert"):
        table = models.Base.metadata.tables[table_name]
        ddl = str(CreateTable(table).compile(dialect=mysql.dialect()))
        names = {"source_name", "source_url", "source_record_id"} if table_name in {"disease", "pests"} else AUDIT_COLUMNS
        names = names | ({"category"} if table_name == "plant_diary" else {"session_id", "region_id"} if table_name == "webcam_alert" else set())
        for name in names:
            column_type = str(table.c[name].type.compile(dialect=mysql.dialect()))
            assert f"{name} {column_type}" in ddl
            assert any(statement.startswith(f"ALTER TABLE {table_name} ADD COLUMN {name} {column_type}")
                       for statement in statements), (table_name, name, statements)
        if table_name in {"plant_diary", "webcam_alert"}:
            assert f"ALTER TABLE {table_name} ADD COLUMN requires_review BOOL NOT NULL DEFAULT true" in statements
            assert f"ALTER TABLE {table_name} ADD COLUMN grounding_source VARCHAR(64) NOT NULL DEFAULT 'legacy_unverified'" in statements
    assert "AUTO_INCREMENT" in str(CreateTable(models.WebcamAlert.__table__).compile(dialect=mysql.dialect()))
    user_ddl = str(CreateTable(models.User.__table__).compile(dialect=mysql.dialect()))
    assert "email_verified_at DATETIME" in user_ddl and "email_verified_at DATETIME NOT NULL" not in user_ddl
