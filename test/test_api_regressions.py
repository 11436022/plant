"""Isolated API and schema regressions; no live AI, mail, or production database."""
import io
import os
import sys
from datetime import datetime
from pathlib import Path

for _k, _v in dict(GEMINI_API_KEY="test-key", DB_USER="test", DB_PASSWORD="test", DB_HOST="127.0.0.1",
                  DB_NAME="isolated_test", JWT_SECRET_KEY="isolated-test-only-secret-do-not-use-in-production").items():
    os.environ.setdefault(_k, _v)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from app.db import models
from app.db.session import get_db
from app.routers import auth, prediction, diaries, webcam, admin
from app.services import webcam as webcam_service
from app.services.auth import create_access_token


@pytest.fixture(scope="module")
def password_hash():
    return auth.pwd_context.hash("local-test-password")


@pytest.fixture
def runtime(tmp_path, monkeypatch, password_hash):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    models.Base.metadata.create_all(engine)
    db = Session(engine)
    for uid, name, verified in [(1, "owner", True), (2, "other", True), (3, "unverified", False), (4, "administrator", True)]:
        db.add(models.User(user_id=uid, username=name, password_hash=password_hash, email=f"{name}@example.com",
                           is_email_verified=verified, email_verified_at=datetime(2026, 1, 1) if verified else None,
                           role="admin" if uid == 4 else "user"))
    db.add(models.Crop(crop_id=1, crop_name="Tomato"))
    db.add(models.Disease(disease_id=1, crop_id=1, disease_name="Test disease", description="Database symptoms",
                          treatment="Database advice", source_name="Test fixture", source_url="https://example.com/test-only",
                          source_record_id="test-only"))
    db.commit()
    upload_dir, temp_dir = tmp_path / "uploads", tmp_path / "tmp"
    upload_dir.mkdir()
    temp_dir.mkdir()
    monkeypatch.setattr(settings, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(prediction, "TEMP_DIR", temp_dir)
    monkeypatch.setattr(webcam, "TEMP_DIR", temp_dir)
    monkeypatch.setattr(webcam, "alert_consensus", webcam_service.AlertConsensusTracker())
    monkeypatch.setattr(webcam_service, "send_email", lambda **kwargs: None)
    monkeypatch.setattr(auth, "issue_email_verification", lambda *a, **kw: None)
    prediction.prediction_cache.clear()
    app = FastAPI()
    app.include_router(admin.router)
    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(prediction.router, prefix="/api/v1")
    app.include_router(diaries.router, prefix="/api/v1/diaries")
    app.include_router(webcam.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, raise_server_exceptions=False) as client:
        headers = {u.user_id: {"Authorization": "Bearer " + create_access_token({"user_id": u.user_id, "sub": u.username})}
                   for u in db.query(models.User).all()}
        yield dict(client=client, db=db, headers=headers, temporary=temp_dir, uploads=upload_dir)
    prediction.prediction_cache.clear()
    db.close()
    engine.dispose()


def frame():
    image = Image.new("RGB", (640, 480), "gray")
    draw = ImageDraw.Draw(image)
    for x in range(0, 640, 20):
        draw.line((x, 0, 0, x), fill="green", width=10)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def diagnosis():
    return {"crop_name": "Tomato", "category": "disease", "status_name": "Test disease", "confidence": 0.95,
            "suggestion": "fabricated-model-text", "treatment": "fabricated-model-advice"}


def test_registration_allows_pending_verification(runtime):
    r = runtime["client"].post("/api/v1/auth/users/register", json={"username": "new-user", "password": "local-test-password", "email": "new-user@example.com"})
    assert r.status_code == 200, r.text
    user = runtime["db"].query(models.User).filter_by(username="new-user").one()
    assert user.email_verified_at is None and not user.is_email_verified


def test_verified_login_and_unverified_rejection(runtime):
    c = runtime["client"]
    r = c.post("/api/v1/auth/login", data={"username": "owner", "password": "local-test-password"})
    assert r.status_code == 200
    assert c.get("/api/v1/auth/user/me", headers={"Authorization": "Bearer " + r.json()["access_token"]}).status_code == 200
    assert c.post("/api/v1/auth/login", data={"username": "unverified", "password": "local-test-password"}).status_code == 403


@pytest.mark.parametrize("path", ["/api/v1/predict/", "/api/v1/webcam/analyze"])
def test_invalid_image_returns_client_error(runtime, path):
    r = runtime["client"].post(path, headers=runtime["headers"][1], files={"file": ("bad.jpg", b"not an image", "image/jpeg")})
    assert r.status_code == 400, r.text


def test_review_flag_survives_confirmation(runtime, monkeypatch):
    monkeypatch.setattr(prediction, "diagnostic_plant", lambda *a: {"crop_name": "Tomato", "category": "unknown", "status_name": "Unknown", "confidence": 0.4})
    c = runtime["client"]
    result = c.post("/api/v1/predict/", headers=runtime["headers"][1], files={"file": ("leaf.jpg", frame(), "image/jpeg")}).json()
    assert result["analysis_result"]["requires_review"]
    saved = c.post("/api/v1/diaries/confirm/" + result["prediction_id"], headers=runtime["headers"][1],
                   json={"disease_name": "forged", "gemini_advice": "forged"}).json()["data"]
    assert saved["requires_review"] and saved["category"] == "unknown"
    assert runtime["db"].get(models.PlantDiary, saved["id"]).requires_review


def test_upload_requires_authentication(runtime):
    assert runtime["client"].post("/api/v1/predict/", files={"file": ("leaf.jpg", frame(), "image/jpeg")}).status_code == 401


def test_prediction_owner_expiry_and_duplicate_confirm(runtime, monkeypatch):
    monkeypatch.setattr(prediction, "diagnostic_plant", lambda *a: diagnosis())
    c = runtime["client"]
    result = c.post("/api/v1/predict/", headers=runtime["headers"][1], files={"file": ("leaf.jpg", frame(), "image/jpeg")}).json()
    url = "/api/v1/diaries/confirm/" + result["prediction_id"]
    payload = {"disease_name": "ignored", "gemini_advice": "ignored"}
    assert c.post(url, headers=runtime["headers"][2], json=payload).status_code == 404
    assert c.post(url, headers=runtime["headers"][1], json=payload).status_code == 201
    assert c.post(url, headers=runtime["headers"][1], json=payload).status_code == 404
    result = c.post("/api/v1/predict/", headers=runtime["headers"][1], files={"file": ("leaf.jpg", frame(), "image/jpeg")}).json()
    prediction.prediction_cache[result["prediction_id"]]["expires_at"] = 0
    assert c.post("/api/v1/diaries/confirm/" + result["prediction_id"], headers=runtime["headers"][1], json=payload).status_code == 404
    assert not list(runtime["temporary"].glob("*"))


@pytest.mark.parametrize("method,path", [("get", "/admin/"), ("get", "/admin/users/"), ("get", "/admin/all-diaries"), ("post", "/admin/add"), ("post", "/admin/update/1"), ("post", "/admin/delete/1")])
def test_admin_denies_unauthenticated_and_regular_users(runtime, method, path):
    request = getattr(runtime["client"], method)
    assert request(path).status_code == 401
    assert request(path, headers=runtime["headers"][1]).status_code == 403


def test_admin_login_cookie_role_and_cross_origin(runtime):
    c = runtime["client"]
    assert c.post("/admin/login", data={"username": "owner", "password": "local-test-password"}).status_code == 403
    r = c.post("/admin/login", data={"username": "administrator", "password": "local-test-password"}, follow_redirects=False)
    assert r.status_code == 303
    assert "HttpOnly" in r.headers["set-cookie"] and "SameSite=strict" in r.headers["set-cookie"]
    assert c.post("/admin/logout", headers={"Origin": "https://example.net"}, follow_redirects=False).status_code == 403
    assert c.post("/admin/logout", follow_redirects=False).status_code == 303


def test_cross_crop_same_name_and_source_snapshot(runtime, monkeypatch):
    db = runtime["db"]
    db.add(models.Crop(crop_id=2, crop_name="Other crop"))
    db.add(models.Disease(disease_id=2, crop_id=2, disease_name="Test disease", description="Other symptoms", treatment="Other advice",
                         source_name="Other fixture", source_url="https://example.com/other", source_record_id="other"))
    db.commit()
    monkeypatch.setattr(prediction, "diagnostic_plant", lambda *a: dict(diagnosis(), crop_name="Other crop"))
    c = runtime["client"]
    result = c.post("/api/v1/predict/", headers=runtime["headers"][1], files={"file": ("leaf.jpg", frame(), "image/jpeg")}).json()
    saved = c.post("/api/v1/diaries/confirm/" + result["prediction_id"], headers=runtime["headers"][1],
                   json={"disease_name": "forged", "gemini_advice": "forged"}).json()["data"]
    entry = db.get(models.PlantDiary, saved["id"])
    assert entry.disease_id == 2 and entry.crop_id == 2
    assert saved["reference_record_id"] == entry.reference_record_id == "other"
    assert entry.requires_review is False
    db.get(models.Disease, 2).source_record_id = "updated"
    db.commit()
    db.expire_all()
    assert db.get(models.PlantDiary, saved["id"]).reference_record_id == "other"


def test_webcam_sessions_and_regions_do_not_share_streak(runtime, monkeypatch):
    monkeypatch.setattr(webcam, "diagnostic_plant", lambda *a: diagnosis())
    c = runtime["client"]
    def scan(session, region):
        r = c.post("/api/v1/webcam/analyze", headers=runtime["headers"][1],
                   data={"session_id": session, "region_id": region}, files={"file": ("leaf.jpg", frame(), "image/jpeg")})
        assert r.status_code == 200, r.text
        return r.json()
    for region in ("one", "two"):
        assert scan("session-a", region)["monitoring"]["streak"] == 1
    assert scan("session-b", "one")["monitoring"]["streak"] == 1
    assert scan("session-a", "one")["monitoring"]["streak"] == 2
    result = scan("session-a", "one")
    assert result["monitoring"]["triggered"]
    assert result["alert"]["region_id"] == "one"
    assert result["alert"]["reference_record_id"] == "test-only"


def test_migration_chain_in_isolated_sqlite():
    import importlib.util
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect
    engine = create_engine("sqlite://")
    root = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    names = ["2f64de060dd9_create_initial_tables.py", "8766043b40ed_align_database_with_current_models.py",
             "a11e7c4d9f20_add_webcam_alerts.py", "c37f8e92a411_add_reference_sources.py", "d42a91c8e510_preserve_diagnosis_audit.py"]
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            for name in names:
                spec = importlib.util.spec_from_file_location("migration_" + name[:12], root / name)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                module.upgrade()
        schema = inspect(conn)
        assert next(c for c in schema.get_columns("user") if c["name"] == "email_verified_at")["nullable"]
        assert {"reference_record_id", "requires_review", "category"} <= {c["name"] for c in schema.get_columns("plant_diary")}
        assert {"session_id", "region_id", "requires_review"} <= {c["name"] for c in schema.get_columns("webcam_alert")}
    engine.dispose()
