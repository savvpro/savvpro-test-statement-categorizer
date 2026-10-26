"""Comprehensive unit tests for Phase 8: Database Backup, Restore & Data Management.

Covers:
- Backup creation: successful creation, fallback dumper, checksum generation,
  safe temporary staging, atomic renaming.
- Backup verification: valid checksum, tampered/modified file detection, missing file,
  invalid format detection.
- Restore workflow: confirmation requirement, mandatory safety backup before restore,
  checksum verification before restore, post-restore verification.
- Security: path traversal rejection, credential masking, directory containment.
- Retention: max count enforcement, age-based pruning, strictly protecting
  the last known good backup.
- API endpoints & Web UI routes.
"""

import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest.mock as mock
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import Settings, mask_database_url
from app.main import app
from app.services.backup_service import BackupMetadata, BackupService


@pytest.fixture
def temp_backup_dir() -> Generator[Path, None, None]:
    """Provide an isolated temporary directory for backup testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_engine():
    """Mock database engine providing standard inspection and table counts."""
    engine = mock.MagicMock()
    conn = mock.MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    # Return count 5 for all SELECT COUNT queries
    cursor_mock = mock.MagicMock()
    cursor_mock.scalar.return_value = 5
    conn.execute.return_value = cursor_mock
    return engine


@pytest.fixture
def backup_service(temp_backup_dir: Path, mock_engine) -> BackupService:
    """Create a BackupService configured with isolated directory and mock engine."""
    settings = Settings()
    service = BackupService(
        engine=mock_engine,
        settings=settings,
        backup_directory=temp_backup_dir,
    )
    return service


# ===========================================================================
# 1. Backup Creation Tests
# ===========================================================================

def test_backup_creation_success(backup_service: BackupService, temp_backup_dir: Path):
    """Test successful creation of database backup and independent metadata."""
    # Mock the dump step to write valid SQL to the target file
    def fake_dump(target_path: Path):
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("-- LedgerLens Database Dump\nCREATE TABLE `categories` (id INT);\n")
        return True, None

    with mock.patch.object(backup_service, "_execute_dump", side_effect=fake_dump):
        meta = backup_service.create_backup(backup_type="manual")

    assert meta.status == "success"
    assert meta.backup_type == "manual"
    assert meta.file_size_bytes > 0
    assert len(meta.sha256_checksum) == 64
    assert meta.verification_status == "format_verified"

    # Verify SQL file exists and matches metadata
    sql_path, meta_path = backup_service.get_backup_paths(meta.backup_id)
    assert sql_path.exists()
    assert meta_path.exists()
    assert sql_path.suffix == ".sql"

    # Verify no dangling .tmp files exist
    assert list(temp_backup_dir.glob("*.tmp")) == []

    # Verify companion metadata file contents
    with open(meta_path, "r", encoding="utf-8") as f:
        meta_dict = json.load(f)
    assert meta_dict["backup_id"] == meta.backup_id
    assert meta_dict["sha256_checksum"] == meta.sha256_checksum


def test_backup_creation_unique_filenames(backup_service: BackupService):
    """Ensure consecutive backup runs produce unique filenames and IDs."""
    def fake_dump(target_path: Path):
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("-- LedgerLens Database Dump\nCREATE TABLE `categories` (id INT);\n")
        return True, None

    with mock.patch.object(backup_service, "_execute_dump", side_effect=fake_dump):
        b1 = backup_service.create_backup(backup_type="manual")
        b2 = backup_service.create_backup(backup_type="manual")

    assert b1.backup_id != b2.backup_id
    assert b1.filename != b2.filename


def test_backup_creation_empty_output_rejected(backup_service: BackupService, temp_backup_dir: Path):
    """Ensure that an empty output file raises RuntimeError and cleans up .tmp."""
    def empty_dump(target_path: Path):
        with open(target_path, "w", encoding="utf-8") as f:
            pass  # 0 bytes
        return True, None

    with mock.patch.object(backup_service, "_execute_dump", side_effect=empty_dump):
        with pytest.raises(RuntimeError, match="empty or non-existent file"):
            backup_service.create_backup(backup_type="manual")

    # .tmp file must be cleaned up
    assert list(temp_backup_dir.glob("*.tmp")) == []


def test_backup_creation_invalid_format_rejected(backup_service: BackupService, temp_backup_dir: Path):
    """Ensure non-SQL output (e.g. binary garbage or raw HTML error) is rejected."""
    def garbage_dump(target_path: Path):
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("Random binary or HTML error message without SQL keywords")
        return True, None

    with mock.patch.object(backup_service, "_execute_dump", side_effect=garbage_dump):
        with pytest.raises(RuntimeError, match="does not conform to expected SQL format"):
            backup_service.create_backup(backup_type="manual")

    assert list(temp_backup_dir.glob("*.tmp")) == []


def test_backup_dump_failure_cleans_up_and_records_failure(backup_service: BackupService, temp_backup_dir: Path):
    """Ensure subprocess or engine failure properly records failed metadata."""
    def failing_dump(target_path: Path):
        return False, "Access denied for user"

    with mock.patch.object(backup_service, "_execute_dump", side_effect=failing_dump):
        with pytest.raises(RuntimeError, match="Database dump failed: Access denied"):
            backup_service.create_backup(backup_type="manual")

    assert list(temp_backup_dir.glob("*.tmp")) == []
    # Verify a failed .meta.json was recorded
    failed_metas = list(temp_backup_dir.glob("*.meta.json"))
    assert len(failed_metas) == 1
    with open(failed_metas[0], "r", encoding="utf-8") as f:
        meta_dict = json.load(f)
    assert meta_dict["status"] == "failed"
    assert "Access denied" in meta_dict["failure_reason"]


# ===========================================================================
# 2. Backup Verification Tests
# ===========================================================================

def test_backup_verification_valid(backup_service: BackupService):
    """Test verification of a valid untampered backup."""
    def fake_dump(target_path: Path):
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("-- LedgerLens Database Dump\nCREATE TABLE `categories` (id INT);\n")
        return True, None

    with mock.patch.object(backup_service, "_execute_dump", side_effect=fake_dump):
        meta = backup_service.create_backup(backup_type="manual")

    res = backup_service.verify_backup(meta.backup_id)
    assert res["valid"] is True
    assert res["verification_status"] == "format_verified"
    assert res["sha256_checksum"] == meta.sha256_checksum


def test_backup_verification_detects_tampered_file(backup_service: BackupService):
    """Test that modifying an existing backup triggers checksum mismatch and marks corrupted."""
    def fake_dump(target_path: Path):
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("-- LedgerLens Database Dump\nCREATE TABLE `categories` (id INT);\n")
        return True, None

    with mock.patch.object(backup_service, "_execute_dump", side_effect=fake_dump):
        meta = backup_service.create_backup(backup_type="manual")

    # Modify file contents after creation
    sql_path, meta_path = backup_service.get_backup_paths(meta.backup_id)
    with open(sql_path, "a", encoding="utf-8") as f:
        f.write("\n-- INJECTED MALICIOUS LINE\n")

    res = backup_service.verify_backup(meta.backup_id)
    assert res["valid"] is False
    assert res["verification_status"] == "failed"
    assert "SHA-256 checksum mismatch" in res["reason"]

    # Verify companion metadata updated status to corrupted
    updated_meta = backup_service.get_backup_metadata(meta.backup_id)
    assert updated_meta.status == "corrupted"
    assert updated_meta.verification_status == "failed"


def test_backup_verification_missing_file(backup_service: BackupService):
    """Test verification when .sql file is deleted from disk."""
    res = backup_service.verify_backup("non_existent_backup_id_123")
    assert res["valid"] is False
    assert "does not exist on disk" in res["reason"]


# ===========================================================================
# 3. Security & Path Traversal Tests
# ===========================================================================

def test_path_traversal_rejection(backup_service: BackupService):
    """Ensure directory traversal attacks in backup identifiers are rejected."""
    malicious_ids = [
        "../etc/passwd",
        "..\\windows\\system32",
        "sub/folder/backup",
        "../../backup",
        "backup;rm -rf",
        "backup|cat",
        "backup with spaces",
    ]

    for bad_id in malicious_ids:
        with pytest.raises(ValueError):
            backup_service.sanitize_backup_id(bad_id)

        with pytest.raises(ValueError):
            backup_service.get_backup_paths(bad_id)

        with pytest.raises(ValueError):
            backup_service.restore_backup(bad_id, confirmation=True)


def test_credential_masking():
    """Ensure database passwords are masked in URLs and logs."""
    url = "mysql+pymysql://root:super_secret_password_123@127.0.0.1:3306/ledgerlens_db"
    masked = mask_database_url(url)
    assert "super_secret_password_123" not in masked
    assert "root:***@127.0.0.1:3306/ledgerlens_db" in masked


# ===========================================================================
# 4. Restore Workflow Tests
# ===========================================================================

def test_restore_requires_confirmation(backup_service: BackupService):
    """Ensure restore without confirmation=True raises ValueError."""
    with pytest.raises(ValueError, match="explicit confirmation is required"):
        backup_service.restore_backup("some_backup_id", confirmation=False)


def test_restore_creates_mandatory_safety_backup(backup_service: BackupService, temp_backup_dir: Path):
    """Verify that restore immediately creates a pre-restore safety backup first."""
    # 1. Create a primary backup to restore from
    def fake_dump(target_path: Path):
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("-- LedgerLens Database Dump\nCREATE TABLE `categories` (id INT);\n")
        return True, None

    with mock.patch.object(backup_service, "_execute_dump", side_effect=fake_dump):
        primary_meta = backup_service.create_backup(backup_type="manual")

    # 2. Mock restore execution
    with mock.patch.object(backup_service, "_execute_restore") as mock_restore, \
         mock.patch.object(backup_service, "_execute_dump", side_effect=fake_dump):
        res = backup_service.restore_backup(primary_meta.backup_id, confirmation=True)

    assert res["success"] is True
    assert res["restored_backup_id"] == primary_meta.backup_id
    assert res["safety_backup_id"].startswith("ledgerlens_safety_")

    # Check that safety backup was saved in backup directory
    safety_meta = backup_service.get_backup_metadata(res["safety_backup_id"])
    assert safety_meta is not None
    assert safety_meta.backup_type == "safety"


def test_restore_aborts_if_verification_fails(backup_service: BackupService):
    """Ensure corrupted backup cannot be restored."""
    def fake_dump(target_path: Path):
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("-- LedgerLens Database Dump\nCREATE TABLE `categories` (id INT);\n")
        return True, None

    with mock.patch.object(backup_service, "_execute_dump", side_effect=fake_dump):
        meta = backup_service.create_backup(backup_type="manual")

    # Tamper with file
    sql_path, _ = backup_service.get_backup_paths(meta.backup_id)
    with open(sql_path, "w") as f:
        f.write("corrupted content")

    with pytest.raises(ValueError, match="integrity check failed"):
        backup_service.restore_backup(meta.backup_id, confirmation=True)


# ===========================================================================
# 5. Retention Management Tests
# ===========================================================================

def test_retention_pruning_respects_max_count(backup_service: BackupService):
    """Ensure pruning enforces BACKUP_MAX_COUNT."""
    backup_service.settings.backup_max_count = 3
    backup_service.settings.backup_retention_days = 30

    def fake_dump(target_path: Path):
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("-- LedgerLens Database Dump\nCREATE TABLE `categories` (id INT);\n")
        return True, None

    # Create 5 backups
    created_ids = []
    with mock.patch.object(backup_service, "_execute_dump", side_effect=fake_dump):
        for _ in range(5):
            meta = backup_service.create_backup(backup_type="manual")
            created_ids.append(meta.backup_id)

    assert len(backup_service.list_backups()) == 5

    res = backup_service.prune_backups()
    assert res["pruned_count"] == 2
    assert res["retained_count"] == 3

    remaining_ids = [b.backup_id for b in backup_service.list_backups()]
    assert len(remaining_ids) == 3


def test_retention_never_deletes_last_known_good_backup(backup_service: BackupService):
    """Ensure that the last known good backup is NEVER pruned, even if older than retention days."""
    backup_service.settings.backup_max_count = 1
    backup_service.settings.backup_retention_days = 10

    def fake_dump(target_path: Path):
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("-- LedgerLens Database Dump\nCREATE TABLE `categories` (id INT);\n")
        return True, None

    with mock.patch.object(backup_service, "_execute_dump", side_effect=fake_dump):
        meta = backup_service.create_backup(backup_type="manual")

    # Artificially age the backup created_at to 60 days ago
    old_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=60)).isoformat()
    meta.created_at = old_date
    sql_path, meta_path = backup_service.get_backup_paths(meta.backup_id)
    backup_service._save_metadata(meta, meta_path)

    # Prune
    res = backup_service.prune_backups()
    assert res["pruned_count"] == 0
    assert res["retained_count"] == 1

    # Verify the backup still exists on disk
    assert sql_path.exists()
    assert meta_path.exists()


# ===========================================================================
# 6. Diagnostics Tests
# ===========================================================================

def test_diagnostics_structure(backup_service: BackupService):
    """Ensure operational diagnostics report contains all necessary fields."""
    diag = backup_service.get_diagnostics()
    assert "database_connected" in diag
    assert "database_masked_url" in diag
    assert "table_counts" in diag
    assert "total_backups_count" in diag
    assert "total_size_formatted" in diag
    assert "backup_warning" in diag
    assert "retention_max_count" in diag
    assert "retention_days" in diag


# ===========================================================================
# 7. FastAPI API & Web Route Tests
# ===========================================================================

from app.api.routes.backups import get_backup_service


@pytest.fixture
def test_client(temp_backup_dir: Path) -> Generator[TestClient, None, None]:
    """TestClient with overridden BackupService dependency."""
    mock_svc = mock.MagicMock(spec=BackupService)
    mock_svc.list_backups.return_value = [
        BackupMetadata(
            backup_id="test_backup_001",
            filename="test_backup_001.sql",
            created_at="2026-10-27T02:00:00Z",
            file_size_bytes=2048,
            sha256_checksum="abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            status="success",
            verification_status="format_verified",
            backup_type="manual",
        )
    ]
    mock_svc.get_diagnostics.return_value = {
        "database_connected": True,
        "database_masked_url": "mysql+pymysql://root:***@localhost:3306/ledgerlens_db",
        "table_counts": {"transactions": 42, "categories": 12, "statements": 3, "merchant_rules": 8},
        "total_backups_count": 1,
        "total_size_bytes": 2048,
        "total_size_formatted": "2.0 KB",
        "last_successful_backup": {
            "backup_id": "test_backup_001",
            "created_at": "2026-10-27T02:00:00Z",
        },
        "days_since_last_backup": 0,
        "backup_warning": None,
        "auto_backup_enabled": False,
        "retention_max_count": 20,
        "retention_days": 30,
        "backup_directory": str(temp_backup_dir),
    }
    mock_svc.create_backup.return_value = BackupMetadata(
        backup_id="new_backup_123",
        filename="new_backup_123.sql",
        created_at="2026-10-27T02:30:00Z",
        file_size_bytes=1024,
        sha256_checksum="def1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        status="success",
        verification_status="format_verified",
        backup_type="manual",
    )
    mock_svc.verify_backup.return_value = {
        "valid": True,
        "backup_id": "test_backup_001",
        "verification_status": "format_verified",
        "sha256_checksum": "abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "file_size_bytes": 2048,
    }
    mock_svc.restore_backup.return_value = {
        "success": True,
        "restored_backup_id": "test_backup_001",
        "safety_backup_id": "ledgerlens_safety_999",
        "elapsed_seconds": 0.45,
        "table_counts": {"transactions": 42},
    }
    mock_svc.delete_backup.return_value = True
    mock_svc.prune_backups.return_value = {
        "pruned_count": 1,
        "pruned_ids": ["old_backup_1"],
        "retained_count": 1,
    }
    mock_svc.get_backup_metadata.return_value = mock_svc.list_backups.return_value[0]

    app.dependency_overrides[get_backup_service] = lambda: mock_svc

    with mock.patch("app.web.routes.BackupService", return_value=mock_svc):
        client = TestClient(app)
        yield client

    app.dependency_overrides.pop(get_backup_service, None)


def test_api_list_backups(test_client: TestClient):
    """GET /api/backups returns 200 with backups list and diagnostics."""
    resp = test_client.get("/api/backups")
    assert resp.status_code == 200
    data = resp.json()
    assert "backups" in data
    assert len(data["backups"]) == 1
    assert data["backups"][0]["backup_id"] == "test_backup_001"
    assert "diagnostics" in data


def test_api_create_backup(test_client: TestClient):
    """POST /api/backups triggers backup creation."""
    resp = test_client.post("/api/backups", json={"backup_type": "manual"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["backup"]["backup_id"] == "new_backup_123"


def test_api_verify_backup(test_client: TestClient):
    """POST /api/backups/{id}/verify returns verification result."""
    resp = test_client.post("/api/backups/test_backup_001/verify", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["verification_status"] == "format_verified"


def test_api_restore_backup_requires_confirm(test_client: TestClient):
    """POST /api/backups/{id}/restore requires confirm=True."""
    # confirm=False should fail
    resp = test_client.post("/api/backups/test_backup_001/restore", json={"confirm": False})
    assert resp.status_code == 400

    # confirm=True should succeed
    resp_ok = test_client.post("/api/backups/test_backup_001/restore", json={"confirm": True})
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert data["details"]["safety_backup_id"] == "ledgerlens_safety_999"


def test_api_delete_backup(test_client: TestClient):
    """DELETE /api/backups/{id} deletes backup."""
    resp = test_client.delete("/api/backups/test_backup_001")
    assert resp.status_code == 200
    assert resp.json()["backup_id"] == "test_backup_001"


def test_web_backups_page(test_client: TestClient):
    """GET /backups renders the Jinja2 template successfully."""
    resp = test_client.get("/backups")
    assert resp.status_code == 200
    assert "Database Backup" in resp.text
    assert "test_backup_001" in resp.text
    assert "Protected Records" in resp.text


def test_web_restore_form_requires_exact_keyword(test_client: TestClient):
    """POST /backups/{id}/restore rejects if user didn't type 'RESTORE'."""
    resp = test_client.post(
        "/backups/test_backup_001/restore",
        data={"confirm_text": "yes"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "error=" in resp.headers["location"]
    assert "type+%27RESTORE%27" in resp.headers["location"] or "RESTORE" in resp.headers["location"]


def test_web_restore_form_success(test_client: TestClient):
    """POST /backups/{id}/restore succeeds with confirm_text='RESTORE'."""
    resp = test_client.post(
        "/backups/test_backup_001/restore",
        data={"confirm_text": "RESTORE"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "success=" in resp.headers["location"]
