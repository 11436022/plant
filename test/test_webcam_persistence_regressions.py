"""Alert transaction and image-lifetime regressions; no external services."""
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.orm import Session

from test_api_regressions import diagnosis, frame, password_hash, runtime
from test_backend_manifest_regressions import no_external_io
from app.core.config import settings
from app.db import models
from app.routers import webcam
from app.services import webcam as webcam_service


@pytest.fixture
def alert_runtime(runtime, monkeypatch):
    monkeypatch.setattr(settings, "WEBCAM_ALERT_CONSECUTIVE_MATCHES", 1)
    monkeypatch.setattr(settings, "WEBCAM_ALERT_CONFIDENCE", 0.8)
    monkeypatch.setattr(webcam, "diagnostic_plant", lambda *args: diagnosis())
    email = Mock()
    monkeypatch.setattr(webcam_service, "send_email", email)
    return dict(runtime, content=frame(), email=email)


def _analyze(runtime):
    return runtime["client"].post(
        "/api/v1/webcam/analyze", headers=runtime["headers"][1],
        data={"session_id": "save-session", "region_id": "save-region"},
        files={"file": ("leaf.jpg", runtime["content"], "image/jpeg")},
    )


def _assert_clean(runtime):
    with Session(runtime["db"].get_bind()) as verification:
        assert verification.query(models.WebcamAlert).count() == 0
    assert not list(runtime["uploads"].iterdir())
    assert not list(runtime["temporary"].iterdir())


def _assert_saved(runtime, *, email_sent):
    with Session(runtime["db"].get_bind()) as verification:
        alert = verification.query(models.WebcamAlert).one()
        assert alert.email_sent is email_sent and alert.created_at is not None
        assert alert.reference_record_id == "test-only" and alert.requires_review is False
        assert (alert.session_id, alert.region_id) == ("save-session", "save-region")
        image = Path(alert.image_url)
        assert image.parent == runtime["uploads"] and image.read_bytes() == runtime["content"]
        alert_id = alert.id
    assert list(runtime["uploads"].iterdir()) == [image]
    assert not list(runtime["temporary"].iterdir())
    return alert_id


@pytest.mark.parametrize("failure", ["refresh", "serialize", "serialize_http"])
def test_precommit_failure_rolls_back_alert_and_removes_image(alert_runtime, monkeypatch, failure):
    db = alert_runtime["db"]
    commit = Mock(wraps=db.commit)
    monkeypatch.setattr(db, "commit", commit)
    expected = 409 if failure == "serialize_http" else 500
    error = HTTPException(status_code=409, detail="Serialization rejected") if expected == 409 else RuntimeError("Injected failure")
    broken = Mock(side_effect=error)
    if failure == "refresh":
        monkeypatch.setattr(db, "refresh", broken)
    else:
        monkeypatch.setattr(webcam, "serialize_webcam_alert", broken)
    response = _analyze(alert_runtime)
    assert response.status_code == expected, response.text
    broken.assert_called_once()
    commit.assert_not_called()
    alert_runtime["email"].assert_not_called()
    _assert_clean(alert_runtime)


def test_alert_serializes_before_commit_and_never_reloads_expired_models(alert_runtime, monkeypatch):
    db = alert_runtime["db"]
    assert db.expire_on_commit is True
    commits, reloads = [], []
    original_refresh, original_serialize = db.refresh, webcam.serialize_webcam_alert

    def refresh(*args, **kwargs):
        assert not commits, "Refresh must occur before persistence"
        return original_refresh(*args, **kwargs)

    def serialize(alert):
        assert not commits, "Serialize while the transaction is still reversible"
        assert alert.id is not None and alert.created_at is not None
        return original_serialize(alert)

    def after_commit(session):
        commits.append(True)

    def forbid_reload(state):
        if commits and state.is_select:
            reloads.append(state.statement)
            raise AssertionError("No post-commit ORM reads are needed to return the alert")

    def email(**kwargs):
        assert commits == [True], "Notification must follow the alert commit"
        assert kwargs["to_email"] == "owner@example.com"
        assert "Database advice" in kwargs["text_body"]
        _assert_saved_during_email(alert_runtime)

    def _assert_saved_during_email(runtime):
        with Session(db.get_bind()) as verification:
            alert = verification.query(models.WebcamAlert).one()
            assert alert.email_sent is False and Path(alert.image_url).exists()

    refresh_spy, serialize_spy = Mock(side_effect=refresh), Mock(side_effect=serialize)
    monkeypatch.setattr(db, "refresh", refresh_spy)
    monkeypatch.setattr(webcam, "serialize_webcam_alert", serialize_spy)
    alert_runtime["email"].side_effect = email
    event.listen(db, "after_commit", after_commit)
    event.listen(db, "do_orm_execute", forbid_reload)
    try:
        response = _analyze(alert_runtime)
    finally:
        event.remove(db, "do_orm_execute", forbid_reload)
        event.remove(db, "after_commit", after_commit)
    assert response.status_code == 200, response.text
    assert commits == [True, True] and reloads == [] and db.expire_on_commit is True
    refresh_spy.assert_called_once()
    serialize_spy.assert_called_once()
    alert_runtime["email"].assert_called_once()
    payload = response.json()
    assert payload["alert"]["id"] == _assert_saved(alert_runtime, email_sent=True)
    assert payload["alert"]["email_sent"] is True and payload["alert"]["created_at"]
    assert payload["monitoring"]["triggered"] is True
    assert payload["frame"] == {"width": 640, "height": 480, "format": "JPEG"}


@pytest.mark.parametrize("failure", ["smtp", "email_status_commit", "no_recipient"])
def test_notification_failure_keeps_valid_alert_with_email_false(alert_runtime, monkeypatch, failure):
    db = alert_runtime["db"]
    if failure == "smtp":
        alert_runtime["email"].side_effect = RuntimeError("SMTP unavailable")
    elif failure == "email_status_commit":
        original_commit = db.commit
        attempts = []

        def commit():
            attempts.append(True)
            if len(attempts) == 2:
                raise RuntimeError("Email status transaction failed")
            return original_commit()

        monkeypatch.setattr(db, "commit", commit)
    else:
        db.get(models.User, 1).email = None
        db.commit()
    response = _analyze(alert_runtime)
    assert response.status_code == 200, response.text
    assert response.json()["alert"]["email_sent"] is False
    assert response.json()["alert"]["id"] == _assert_saved(alert_runtime, email_sent=False)
    if failure == "no_recipient":
        alert_runtime["email"].assert_not_called()
    else:
        alert_runtime["email"].assert_called_once()
    if failure == "email_status_commit":
        assert attempts == [True, True]


@pytest.mark.parametrize("failure", ["postcommit", "postcommit_http", "response_encoding"])
def test_errors_after_persistence_never_delete_committed_image(alert_runtime, monkeypatch, failure):
    if failure == "response_encoding":
        original_serialize = webcam.serialize_webcam_alert

        def serialize(alert):
            payload = original_serialize(alert)
            payload["created_at"] = object()  # Fails only when FastAPI encodes the returned response.
            return payload

        monkeypatch.setattr(webcam, "serialize_webcam_alert", serialize)
    else:
        error = HTTPException(status_code=409, detail="Post-commit failure") if failure == "postcommit_http" else RuntimeError("Post-commit failure")
        monkeypatch.setattr(webcam, "send_webcam_alert_email", Mock(side_effect=error))
    response = _analyze(alert_runtime)
    assert response.status_code == (409 if failure == "postcommit_http" else 500), response.text
    _assert_saved(alert_runtime, email_sent=failure == "response_encoding")


@pytest.mark.parametrize("commit_reached_database", [False, True])
def test_uncertain_commit_outcome_preserves_image_evidence(alert_runtime, monkeypatch, commit_reached_database):
    db = alert_runtime["db"]
    original_commit = db.commit

    def uncertain_commit():
        if commit_reached_database:
            original_commit()
        raise RuntimeError("Commit result unavailable")

    monkeypatch.setattr(db, "commit", uncertain_commit)
    response = _analyze(alert_runtime)
    assert response.status_code == 500, response.text
    alert_runtime["email"].assert_not_called()
    with Session(db.get_bind()) as verification:
        assert verification.query(models.WebcamAlert).count() == int(commit_reached_database)
    images = list(alert_runtime["uploads"].iterdir())
    assert len(images) == 1 and images[0].read_bytes() == alert_runtime["content"]
    assert not list(alert_runtime["temporary"].iterdir())
    if commit_reached_database:
        _assert_saved(alert_runtime, email_sent=False)
