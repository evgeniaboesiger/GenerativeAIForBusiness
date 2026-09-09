"""
MATCHA - Automated tests for account features:
  - editing the display name
  - tracking submitted applications and their status

A temporary SQLite database is used so the production data is untouched.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))

import db  # noqa: E402


@pytest.fixture()
def isolated_user(tmp_path, monkeypatch):
    """Point the module at a temp DB and create a fresh candidate account."""
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_accounts.db"))
    monkeypatch.setattr(db, "KEY_FILE", str(tmp_path / ".key"))
    return db.register_user("anna@test.ch", "secret123", "Anna Weber", role="candidate")


# ---------------------------------------------------------------------- #
#  Display name editing
# ---------------------------------------------------------------------- #
def test_update_user_name(isolated_user):
    db.update_user_name(isolated_user["id"], "Anna M. Weber")
    refreshed = db.login_user("anna@test.ch", "secret123")
    assert refreshed["full_name"] == "Anna M. Weber"


def test_update_user_name_rejects_empty(isolated_user):
    with pytest.raises(ValueError):
        db.update_user_name(isolated_user["id"], "   ")


# ---------------------------------------------------------------------- #
#  Submitted-application tracking
# ---------------------------------------------------------------------- #
def test_save_and_load_submitted_applications(isolated_user):
    job = {"id": "job_001", "title": "Marketing Manager Digital", "company": "Basel Pharma AG"}
    db.save_submitted_application(isolated_user["id"], job)

    apps = db.load_submitted_applications(isolated_user["id"])
    assert len(apps) == 1
    assert apps[0]["job_title"] == "Marketing Manager Digital"
    assert apps[0]["company"] == "Basel Pharma AG"
    assert apps[0]["status"] == "under_review"
    assert apps[0]["submitted_at"]


def test_applications_listed_newest_first(isolated_user):
    second_job = {"id": "job_002", "title": "Backend Developer", "company": "Swiss Digital Solutions"}
    db.save_submitted_application(isolated_user["id"], {"id": "job_001", "title": "Marketing Manager Digital", "company": "Basel Pharma AG"})
    db.save_submitted_application(isolated_user["id"], second_job)

    apps = db.load_submitted_applications(isolated_user["id"])
    assert [a["job_id"] for a in apps] == ["job_002", "job_001"]
    assert apps[0]["company"] == "Swiss Digital Solutions"


def test_applications_are_per_user(isolated_user):
    job = {"id": "job_001", "title": "Marketing Manager Digital", "company": "Basel Pharma AG"}
    db.save_submitted_application(isolated_user["id"], job)
    other = db.register_user("lena@test.ch", "secret123", "Lena Keller", role="candidate")
    assert db.load_submitted_applications(other["id"]) == []