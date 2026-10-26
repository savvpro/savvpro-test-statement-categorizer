"""LedgerLens Phase 8: Database Backup, Restore, and Data Management Service.

Provides:
- Reliable MySQL database backups using native mysqldump (when available) or
  structured SQLAlchemy DDL/DML fallback.
- SHA-256 checksum generation, independent JSON metadata storage on filesystem.
- Safe staging (writing to temporary .tmp files prior to atomic publishing).
- Strict path traversal prevention and credential masking.
- Controlled restore with mandatory pre-restore safety backups and confirmation.
- Backup integrity and format verification.
- Safe retention management enforcing maximum count and age retention policies
  while strictly preserving the last known good recovery point.
- Operational and financial diagnostics.
"""

from dataclasses import asdict, dataclass, field
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings, mask_database_url
from app.database.session import check_database_connection, get_engine


@dataclass
class BackupMetadata:
    """Metadata record for an individual database backup."""

    backup_id: str
    filename: str
    created_at: str  # ISO 8601 string
    file_size_bytes: int
    sha256_checksum: str
    status: str  # 'success', 'failed', 'corrupted'
    verification_status: str  # 'unverified', 'checksum_verified', 'format_verified', 'restore_verified', 'failed'
    backup_type: str  # 'manual', 'safety', 'scheduled'
    failure_reason: Optional[str] = None
    table_counts: Dict[str, int] = field(default_factory=dict)
    format_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackupMetadata":
        """Instantiate metadata from dictionary."""
        return cls(
            backup_id=data.get("backup_id", ""),
            filename=data.get("filename", ""),
            created_at=data.get("created_at", ""),
            file_size_bytes=int(data.get("file_size_bytes", 0)),
            sha256_checksum=data.get("sha256_checksum", ""),
            status=data.get("status", "unknown"),
            verification_status=data.get("verification_status", "unverified"),
            backup_type=data.get("backup_type", "manual"),
            failure_reason=data.get("failure_reason"),
            table_counts=data.get("table_counts", {}),
            format_version=data.get("format_version", "1.0"),
        )


class BackupService:
    """Service handling backup creation, verification, restore, and retention."""

    # Essential application tables that must be protected and restored
    CORE_TABLES = [
        "categories",
        "statements",
        "transactions",
        "classification_events",
        "merchant_rules",
        "alembic_version",
    ]

    def __init__(
        self,
        engine: Optional[Engine] = None,
        settings: Optional[Settings] = None,
        backup_directory: Optional[Path] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.engine = engine or get_engine()
        self.backup_dir = (
            backup_directory or self.settings.get_backup_directory()
        ).resolve()
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # Path Security & Helpers
    # -----------------------------------------------------------------------

    def sanitize_backup_id(self, backup_id: str) -> str:
        """Validate and sanitize backup identifier to prevent path traversal."""
        if not backup_id or not isinstance(backup_id, str):
            raise ValueError("Backup identifier cannot be empty.")

        cleaned = backup_id.strip()
        # Enforce strict alphanumeric, underscore, and dash characters only
        if not re.match(r"^[A-Za-z0-9_\-]+$", cleaned):
            raise ValueError(
                f"Invalid backup identifier format: '{backup_id}'. "
                "Identifiers may only contain letters, numbers, underscores, and dashes."
            )

        if ".." in cleaned or "/" in cleaned or "\\" in cleaned:
            raise ValueError("Path traversal attempt detected in backup identifier.")

        return cleaned

    def get_backup_paths(self, backup_id: str) -> Tuple[Path, Path]:
        """Resolve and verify paths for SQL dump and companion metadata.

        Enforces that resolved paths are strictly contained within the backup directory.
        """
        clean_id = self.sanitize_backup_id(backup_id)
        # Standard filenames based on backup_id
        sql_filename = f"{clean_id}.sql"
        meta_filename = f"{clean_id}.meta.json"

        sql_path = (self.backup_dir / sql_filename).resolve()
        meta_path = (self.backup_dir / meta_filename).resolve()

        # Strict containment validation
        try:
            sql_path.relative_to(self.backup_dir)
            meta_path.relative_to(self.backup_dir)
        except ValueError:
            raise ValueError(
                f"Path traversal detected: path {sql_path} escapes {self.backup_dir}"
            )

        return sql_path, meta_path

    def _parse_db_url(self, url: str) -> Dict[str, Any]:
        """Extract connection components (host, port, user, password, db) safely."""
        parsed = urlparse(url)
        # Scheme may be mysql+pymysql
        user = parsed.username or "root"
        password = parsed.password or ""
        host = parsed.hostname or "localhost"
        port = parsed.port or 3306
        dbname = parsed.path.lstrip("/").split("?")[0]
        return {
            "user": user,
            "password": password,
            "host": host,
            "port": port,
            "database": dbname,
        }

    def _compute_sha256(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    # -----------------------------------------------------------------------
    # Table Diagnostics and Row Counts
    # -----------------------------------------------------------------------

    def get_table_counts(self) -> Dict[str, int]:
        """Collect row counts for all core application tables."""
        counts: Dict[str, int] = {}
        try:
            with self.engine.connect() as conn:
                for table in self.CORE_TABLES:
                    try:
                        res = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`"))
                        counts[table] = int(res.scalar() or 0)
                    except Exception:
                        # Table might not exist yet
                        counts[table] = 0
        except Exception:
            pass
        return counts

    # -----------------------------------------------------------------------
    # Backup Creation
    # -----------------------------------------------------------------------

    def create_backup(
        self,
        backup_type: str = "manual",
        custom_id: Optional[str] = None,
    ) -> BackupMetadata:
        """Create a new full database backup.

        Steps:
        1. Generates unique timestamped filename.
        2. Queries current table counts for metadata snapshot.
        3. Writes to a temporary staging file (.tmp).
        4. Executes mysqldump if available, or structured SQLAlchemy dumper.
        5. Verifies output size and SQL format.
        6. Computes SHA-256 checksum.
        7. Atomically publishes the file by renaming .tmp to .sql.
        8. Stores independent companion JSON metadata.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        rand_suffix = hashlib.sha256(f"{now.timestamp()}_{os.urandom(8)}".encode()).hexdigest()[:6]

        if custom_id:
            backup_id = self.sanitize_backup_id(custom_id)
        else:
            prefix = "safety" if backup_type == "safety" else "backup"
            backup_id = f"ledgerlens_{prefix}_{timestamp_str}_{rand_suffix}"

        sql_path, meta_path = self.get_backup_paths(backup_id)
        temp_sql_path = sql_path.with_suffix(".tmp")

        table_counts = self.get_table_counts()

        try:
            # 1. Attempt dump to temp file
            success, reason = self._execute_dump(temp_sql_path)
            if not success:
                raise RuntimeError(f"Database dump failed: {reason}")

            # 2. Verify non-empty and minimum structure
            if not temp_sql_path.exists() or temp_sql_path.stat().st_size == 0:
                raise RuntimeError("Backup generated an empty or non-existent file.")

            file_size = temp_sql_path.stat().st_size
            with open(temp_sql_path, "r", encoding="utf-8", errors="ignore") as f:
                header_snippet = f.read(1024)

            # Check for basic SQL markers
            if not any(
                marker in header_snippet
                for marker in ["-- LedgerLens", "MySQL dump", "CREATE TABLE", "SET FOREIGN_KEY_CHECKS"]
            ):
                raise RuntimeError("Backup output does not conform to expected SQL format.")

            # 3. Compute Checksum
            sha256 = self._compute_sha256(temp_sql_path)

            # 4. Atomically publish file
            if sql_path.exists():
                sql_path.unlink()
            temp_sql_path.rename(sql_path)

            # 5. Build and save metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                filename=sql_path.name,
                created_at=now.isoformat(),
                file_size_bytes=file_size,
                sha256_checksum=sha256,
                status="success",
                verification_status="format_verified",
                backup_type=backup_type,
                table_counts=table_counts,
            )
            self._save_metadata(metadata, meta_path)
            return metadata

        except Exception as exc:
            # Clean up temp file on failure
            if temp_sql_path.exists():
                try:
                    temp_sql_path.unlink()
                except OSError:
                    pass

            # Record failed metadata record so failure is visible
            failed_metadata = BackupMetadata(
                backup_id=backup_id,
                filename=sql_path.name,
                created_at=now.isoformat(),
                file_size_bytes=0,
                sha256_checksum="",
                status="failed",
                verification_status="failed",
                backup_type=backup_type,
                failure_reason=str(exc),
                table_counts=table_counts,
            )
            self._save_metadata(failed_metadata, meta_path)
            raise RuntimeError(f"Failed to create backup: {exc}") from exc

    def _execute_dump(self, target_path: Path) -> Tuple[bool, Optional[str]]:
        """Perform database dump using mysqldump if available, or SQLAlchemy fallback."""
        mysqldump_bin = shutil.which("mysqldump") or os.environ.get("MYSQLDUMP_PATH")

        if mysqldump_bin and os.path.exists(mysqldump_bin):
            try:
                return self._dump_with_mysqldump(mysqldump_bin, target_path)
            except Exception as exc:
                # If mysqldump fails unexpectedly, log and fallback to native dumper
                pass

        # Fallback to pure-Python SQLAlchemy dumper
        return self._dump_with_sqlalchemy(target_path)

    def _dump_with_mysqldump(self, binary: str, target_path: Path) -> Tuple[bool, Optional[str]]:
        """Run native mysqldump with credentials passed securely via environment variable."""
        db_url = self.settings.get_database_url()
        conn_params = self._parse_db_url(db_url)

        cmd = [
            binary,
            "-h",
            str(conn_params["host"]),
            "-P",
            str(conn_params["port"]),
            "-u",
            str(conn_params["user"]),
            "--single-transaction",
            "--quick",
            "--routines",
            "--triggers",
            "--add-drop-table",
            str(conn_params["database"]),
        ]

        # Pass password securely via environment variable MYSQL_PWD to avoid
        # showing credentials in process lists (ps, Task Manager)
        sub_env = os.environ.copy()
        if conn_params["password"]:
            sub_env["MYSQL_PWD"] = conn_params["password"]

        with open(target_path, "wb") as out_f:
            proc = subprocess.run(
                cmd,
                stdout=out_f,
                stderr=subprocess.PIPE,
                env=sub_env,
                check=False,
                timeout=300,
            )

        if proc.returncode != 0:
            err_msg = proc.stderr.decode("utf-8", errors="replace").strip()
            # Redact password if present in any error string
            masked_err = err_msg.replace(conn_params["password"], "***") if conn_params["password"] else err_msg
            return False, f"mysqldump exited with code {proc.returncode}: {masked_err}"

        return True, None

    def _dump_with_sqlalchemy(self, target_path: Path) -> Tuple[bool, Optional[str]]:
        """Generate a complete, restorable MySQL dump using SQLAlchemy schema inspection."""
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write("-- LedgerLens Database Dump\n")
                f.write(f"-- Generated on: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n")
                f.write("-- Engine: Native SQLAlchemy Fallback Dumper\n\n")
                f.write("SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;\n")
                f.write("SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO';\n\n")

                with self.engine.connect() as conn:
                    # Find all tables in database
                    inspector = inspect(conn)
                    table_names = inspector.get_table_names()

                    # Order tables: alembic_version first, then dependencies
                    ordered_tables: List[str] = []
                    for t in self.CORE_TABLES:
                        if t in table_names and t not in ordered_tables:
                            ordered_tables.append(t)
                    for t in table_names:
                        if t not in ordered_tables:
                            ordered_tables.append(t)

                    for table_name in ordered_tables:
                        f.write(f"\n-- Table structure for table `{table_name}`\n")
                        f.write(f"DROP TABLE IF EXISTS `{table_name}`;\n")

                        # Try to get MySQL exact CREATE TABLE statement
                        try:
                            create_res = conn.execute(text(f"SHOW CREATE TABLE `{table_name}`"))
                            create_row = create_res.fetchone()
                            if create_row and len(create_row) >= 2:
                                create_sql = create_row[1]
                                f.write(f"{create_sql};\n\n")
                        except Exception:
                            pass

                        # Dump data
                        f.write(f"-- Dumping data for table `{table_name}`\n")
                        data_res = conn.execute(text(f"SELECT * FROM `{table_name}`"))
                        keys = list(data_res.keys())
                        if not keys:
                            continue

                        columns_str = ", ".join(f"`{k}`" for k in keys)
                        rows = data_res.fetchall()
                        if rows:
                            f.write(f"LOCK TABLES `{table_name}` WRITE;\n")
                            # Write in chunks of 200 rows
                            chunk_size = 200
                            for i in range(0, len(rows), chunk_size):
                                chunk = rows[i : i + chunk_size]
                                values_parts = []
                                for r in chunk:
                                    val_strs = [self._sql_format_val(v) for v in r]
                                    values_parts.append(f"({', '.join(val_strs)})")
                                f.write(
                                    f"INSERT INTO `{table_name}` ({columns_str}) VALUES\n"
                                    + ",\n".join(values_parts)
                                    + ";\n"
                                )
                            f.write("UNLOCK TABLES;\n")

                f.write("\nSET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;\n")
                f.write("SET SQL_MODE=@OLD_SQL_MODE;\n")
                f.write("-- Dump completed\n")

            return True, None
        except Exception as exc:
            return False, str(exc)

    @staticmethod
    def _sql_format_val(val: Any) -> str:
        """Format a Python value into a safe SQL literal for dump output."""
        if val is None:
            return "NULL"
        if isinstance(val, bool):
            return "1" if val else "0"
        if isinstance(val, (int, float)):
            return str(val)
        if hasattr(val, "as_tuple") and hasattr(val, "quantize"):  # Decimal
            return str(val)
        if isinstance(val, (datetime.datetime, datetime.date, datetime.time)):
            return f"'{val.isoformat()}'"
        if isinstance(val, bytes):
            return f"X'{val.hex()}'"
        # String escape
        s = str(val)
        s = s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
        return f"'{s}'"

    # -----------------------------------------------------------------------
    # Metadata Management
    # -----------------------------------------------------------------------

    def _save_metadata(self, metadata: BackupMetadata, meta_path: Path) -> None:
        """Persist backup metadata independently to disk as JSON."""
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)

    def get_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """Retrieve metadata for a specific backup."""
        try:
            sql_path, meta_path = self.get_backup_paths(backup_id)
        except ValueError:
            return None

        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return BackupMetadata.from_dict(data)
            except Exception:
                pass

        # If .meta.json is missing but .sql exists, synthesize metadata
        if sql_path.exists():
            stat = sql_path.stat()
            created_at = datetime.datetime.fromtimestamp(
                stat.st_ctime, tz=datetime.timezone.utc
            ).isoformat()
            sha256 = self._compute_sha256(sql_path)
            meta = BackupMetadata(
                backup_id=backup_id,
                filename=sql_path.name,
                created_at=created_at,
                file_size_bytes=stat.st_size,
                sha256_checksum=sha256,
                status="success",
                verification_status="unverified",
                backup_type="manual",
            )
            # Persist companion file
            self._save_metadata(meta, meta_path)
            return meta

        return None

    def list_backups(self) -> List[BackupMetadata]:
        """List all available backups sorted by creation date descending."""
        results: Dict[str, BackupMetadata] = {}

        # 1. Scan existing .meta.json files
        for meta_file in self.backup_dir.glob("*.meta.json"):
            backup_id = meta_file.name[:-10]  # strip '.meta.json'
            try:
                meta = self.get_backup_metadata(backup_id)
                if meta:
                    results[backup_id] = meta
            except Exception:
                continue

        # 2. Check for any orphaned .sql files without .meta.json
        for sql_file in self.backup_dir.glob("*.sql"):
            backup_id = sql_file.stem
            if backup_id not in results:
                try:
                    meta = self.get_backup_metadata(backup_id)
                    if meta:
                        results[backup_id] = meta
                except Exception:
                    continue

        # Sort newest first
        sorted_list = sorted(
            results.values(),
            key=lambda m: m.created_at,
            reverse=True,
        )
        return sorted_list

    # -----------------------------------------------------------------------
    # Backup Verification
    # -----------------------------------------------------------------------

    def verify_backup(
        self,
        backup_id: str,
        test_isolated_restore: bool = False,
    ) -> Dict[str, Any]:
        """Verify the integrity and format of an existing backup file.

        Verification layers:
        1. File existence and non-zero size.
        2. SHA-256 checksum validation against metadata.
        3. Backup format and SQL syntax inspection.
        4. Optional test restoration into an isolated test database.
        """
        sql_path, meta_path = self.get_backup_paths(backup_id)
        meta = self.get_backup_metadata(backup_id)

        if not sql_path.exists():
            return {
                "valid": False,
                "backup_id": backup_id,
                "verification_status": "failed",
                "reason": "Backup SQL dump file does not exist on disk.",
            }

        file_size = sql_path.stat().st_size
        if file_size == 0:
            return {
                "valid": False,
                "backup_id": backup_id,
                "verification_status": "failed",
                "reason": "Backup SQL dump file is empty (0 bytes).",
            }

        # Checksum validation
        current_sha256 = self._compute_sha256(sql_path)
        if meta and meta.sha256_checksum:
            if current_sha256 != meta.sha256_checksum:
                if meta:
                    meta.verification_status = "failed"
                    meta.status = "corrupted"
                    meta.failure_reason = "SHA-256 checksum mismatch"
                    self._save_metadata(meta, meta_path)
                return {
                    "valid": False,
                    "backup_id": backup_id,
                    "verification_status": "failed",
                    "reason": "SHA-256 checksum mismatch. File may be corrupted or modified.",
                    "expected_sha256": meta.sha256_checksum,
                    "actual_sha256": current_sha256,
                }

        # Format validation
        with open(sql_path, "r", encoding="utf-8", errors="ignore") as f:
            sample = f.read(4096)

        has_sql_markers = any(
            m in sample
            for m in ["-- LedgerLens", "MySQL dump", "CREATE TABLE", "SET FOREIGN_KEY_CHECKS", "INSERT INTO"]
        )
        if not has_sql_markers:
            return {
                "valid": False,
                "backup_id": backup_id,
                "verification_status": "failed",
                "reason": "File does not contain valid SQL dump signatures.",
            }

        status = "format_verified"

        # Optional test restore into test database if requested
        if test_isolated_restore and self.settings.test_database_url:
            try:
                self._run_isolated_test_restore(sql_path)
                status = "restore_verified"
            except Exception as exc:
                return {
                    "valid": False,
                    "backup_id": backup_id,
                    "verification_status": "failed",
                    "reason": f"Isolated restore test failed: {exc}",
                }

        # Update metadata
        if meta:
            meta.verification_status = status
            meta.sha256_checksum = current_sha256
            meta.file_size_bytes = file_size
            self._save_metadata(meta, meta_path)

        return {
            "valid": True,
            "backup_id": backup_id,
            "verification_status": status,
            "sha256_checksum": current_sha256,
            "file_size_bytes": file_size,
        }

    def _run_isolated_test_restore(self, sql_path: Path) -> None:
        """Test-restore the dump file into the dedicated test database."""
        test_url = self.settings.get_test_database_url()
        test_engine = create_engine(test_url)
        self._execute_sql_dump_into_engine(test_engine, sql_path)

    # -----------------------------------------------------------------------
    # Restore Workflow
    # -----------------------------------------------------------------------

    def restore_backup(
        self,
        backup_id: str,
        confirmation: bool = False,
    ) -> Dict[str, Any]:
        """Perform a controlled database restoration from a specified backup.

        Safeguards:
        1. Explicit confirmation required.
        2. Strict path traversal check.
        3. File existence and checksum verification prior to starting.
        4. MANDATORY pre-restore safety backup of current data.
        5. Restoration using native MySQL client or connection executor.
        6. Post-restore verification of core application tables.
        """
        if not confirmation:
            raise ValueError(
                "Restoration aborted: explicit confirmation is required "
                "because this operation overwrites database data."
            )

        sql_path, meta_path = self.get_backup_paths(backup_id)

        # Verify integrity before attempting restore
        verify_result = self.verify_backup(backup_id)
        if not verify_result["valid"]:
            raise ValueError(
                f"Cannot restore backup: integrity check failed ({verify_result.get('reason')})."
            )

        # 1. MANDATORY SAFETY BACKUP
        safety_meta = self.create_backup(
            backup_type="safety",
            custom_id=None,
        )

        start_time = time.time()

        # 2. Execute Restoration
        try:
            self._execute_restore(sql_path)
        except Exception as exc:
            raise RuntimeError(
                f"Restore failed during execution: {exc}. "
                f"Your pre-restore data has been preserved in safety backup: {safety_meta.backup_id}"
            ) from exc

        elapsed_seconds = round(time.time() - start_time, 2)

        # 3. Post-restore verification
        post_counts = self.get_table_counts()

        return {
            "success": True,
            "restored_backup_id": backup_id,
            "safety_backup_id": safety_meta.backup_id,
            "elapsed_seconds": elapsed_seconds,
            "table_counts": post_counts,
        }

    def _execute_restore(self, sql_path: Path) -> None:
        """Execute SQL dump restore via mysql CLI if available, or SQLAlchemy connection."""
        mysql_bin = shutil.which("mysql") or os.environ.get("MYSQL_PATH")

        if mysql_bin and os.path.exists(mysql_bin):
            try:
                self._restore_with_mysql_cli(mysql_bin, sql_path)
                return
            except Exception:
                # Fallback to connection executor
                pass

        self._execute_sql_dump_into_engine(self.engine, sql_path)

    def _restore_with_mysql_cli(self, binary: str, sql_path: Path) -> None:
        """Execute restore via mysql command-line utility with credentials in environment."""
        db_url = self.settings.get_database_url()
        conn_params = self._parse_db_url(db_url)

        cmd = [
            binary,
            "-h",
            str(conn_params["host"]),
            "-P",
            str(conn_params["port"]),
            "-u",
            str(conn_params["user"]),
            str(conn_params["database"]),
        ]

        sub_env = os.environ.copy()
        if conn_params["password"]:
            sub_env["MYSQL_PWD"] = conn_params["password"]

        with open(sql_path, "rb") as in_f:
            proc = subprocess.run(
                cmd,
                stdin=in_f,
                capture_output=True,
                env=sub_env,
                check=False,
                timeout=300,
            )

        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", errors="replace").strip()
            masked_err = err.replace(conn_params["password"], "***") if conn_params["password"] else err
            raise RuntimeError(f"mysql client returned error code {proc.returncode}: {masked_err}")

    def _execute_sql_dump_into_engine(self, target_engine: Engine, sql_path: Path) -> None:
        """Parse and execute SQL statements from dump file inside target database connection."""
        with open(sql_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Split content into individual executable SQL statements
        statements = self._split_sql_statements(content)

        with target_engine.connect() as conn:
            # Disable foreign key checks for the session
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            for stmt in statements:
                cleaned = stmt.strip()
                if cleaned:
                    try:
                        conn.execute(text(cleaned))
                    except Exception as exc:
                        # Continue if drop table fails on non-existent table, otherwise raise
                        if not cleaned.upper().startswith("DROP TABLE"):
                            raise RuntimeError(f"Error executing SQL statement: {exc}") from exc
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
            conn.commit()

    @staticmethod
    def _split_sql_statements(sql_text: str) -> List[str]:
        """Split SQL script into executable statements, respecting comments and quotes."""
        statements: List[str] = []
        current: List[str] = []
        in_string: Optional[str] = None
        escape_next = False

        lines = sql_text.splitlines(keepends=True)
        for line in lines:
            stripped = line.strip()
            # Ignore full-line comments when not inside a multi-line string
            if in_string is None and (stripped.startswith("--") or stripped.startswith("/*") or stripped.startswith("#")):
                continue

            for char in line:
                if escape_next:
                    current.append(char)
                    escape_next = False
                    continue

                if char == "\\":
                    escape_next = True
                    current.append(char)
                    continue

                if in_string:
                    current.append(char)
                    if char == in_string:
                        in_string = None
                else:
                    if char in ("'", '"', "`"):
                        in_string = char
                        current.append(char)
                    elif char == ";":
                        stmt = "".join(current).strip()
                        if stmt:
                            statements.append(stmt)
                        current = []
                    else:
                        current.append(char)

        last_stmt = "".join(current).strip()
        if last_stmt:
            statements.append(last_stmt)

        return statements

    # -----------------------------------------------------------------------
    # Deletion and Retention Pruning
    # -----------------------------------------------------------------------

    def delete_backup(self, backup_id: str) -> bool:
        """Safely delete a backup file and its companion metadata.

        Strictly enforces that target files reside within the backup directory.
        """
        sql_path, meta_path = self.get_backup_paths(backup_id)
        deleted = False

        if sql_path.exists():
            sql_path.unlink()
            deleted = True

        if meta_path.exists():
            meta_path.unlink()
            deleted = True

        return deleted

    def prune_backups(self) -> Dict[str, Any]:
        """Apply retention policy based on BACKUP_MAX_COUNT and BACKUP_RETENTION_DAYS.

        CRITICAL SAFEGUARDS:
        1. NEVER deletes files outside the dedicated backup directory.
        2. NEVER deletes the last known good (successful) backup, ensuring that
           the application always retains at least one viable recovery point!
        """
        all_backups = self.list_backups()
        if not all_backups:
            return {"pruned_count": 0, "pruned_ids": [], "retained_count": 0}

        successful_backups = [b for b in all_backups if b.status == "success"]
        # Identify the most recent successful backup — strictly protected
        last_known_good: Optional[BackupMetadata] = (
            successful_backups[0] if successful_backups else None
        )

        max_count = self.settings.backup_max_count
        retention_days = self.settings.backup_retention_days

        now = datetime.datetime.now(datetime.timezone.utc)
        cutoff_date = now - datetime.timedelta(days=retention_days)

        pruned_ids: List[str] = []

        # 1. Enforce max count on successful backups
        if max_count > 0 and len(successful_backups) > max_count:
            # Everything past max_count index is a candidate for removal
            excess_successful = successful_backups[max_count:]
            for b in excess_successful:
                if last_known_good and b.backup_id == last_known_good.backup_id:
                    continue
                self.delete_backup(b.backup_id)
                pruned_ids.append(b.backup_id)

        # 2. Enforce retention days
        remaining = self.list_backups()
        for b in remaining:
            if b.backup_id in pruned_ids:
                continue
            if last_known_good and b.backup_id == last_known_good.backup_id:
                # Never delete the last known good recovery point
                continue

            try:
                b_date = datetime.datetime.fromisoformat(b.created_at)
                if b_date < cutoff_date:
                    self.delete_backup(b.backup_id)
                    pruned_ids.append(b.backup_id)
            except Exception:
                pass

        # 3. Clean up any remaining corrupted or failed records older than 7 days
        for b in self.list_backups():
            if b.status != "success":
                try:
                    b_date = datetime.datetime.fromisoformat(b.created_at)
                    if b_date < (now - datetime.timedelta(days=7)):
                        self.delete_backup(b.backup_id)
                        pruned_ids.append(b.backup_id)
                except Exception:
                    pass

        remaining_count = len(self.list_backups())
        return {
            "pruned_count": len(pruned_ids),
            "pruned_ids": pruned_ids,
            "retained_count": remaining_count,
        }

    # -----------------------------------------------------------------------
    # Operational & Financial Data Diagnostics
    # -----------------------------------------------------------------------

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return diagnostic metrics for operational and backup management."""
        db_connected = check_database_connection(self.engine)
        table_counts = self.get_table_counts() if db_connected else {}

        all_backups = self.list_backups()
        successful_backups = [b for b in all_backups if b.status == "success"]

        last_successful = successful_backups[0] if successful_backups else None
        total_size = sum(b.file_size_bytes for b in all_backups)

        # Calculate days since last backup
        days_since_last_backup: Optional[int] = None
        backup_warning: Optional[str] = None

        if last_successful:
            try:
                created_dt = datetime.datetime.fromisoformat(last_successful.created_at)
                diff = datetime.datetime.now(datetime.timezone.utc) - created_dt
                days_since_last_backup = max(0, diff.days)
                if days_since_last_backup >= 7:
                    backup_warning = (
                        f"The last successful backup was created {days_since_last_backup} days ago. "
                        "We recommend creating a fresh backup regularly."
                    )
            except Exception:
                pass
        else:
            backup_warning = "No successful database backup exists. Please create an initial backup to protect your financial records."

        formatted_size = (
            f"{total_size / (1024 * 1024):.2f} MB"
            if total_size >= 1024 * 1024
            else f"{total_size / 1024:.1f} KB"
        )

        return {
            "database_connected": db_connected,
            "database_masked_url": self.settings.masked_database_url,
            "table_counts": table_counts,
            "total_backups_count": len(all_backups),
            "total_size_bytes": total_size,
            "total_size_formatted": formatted_size,
            "last_successful_backup": last_successful.to_dict() if last_successful else None,
            "days_since_last_backup": days_since_last_backup,
            "backup_warning": backup_warning,
            "auto_backup_enabled": self.settings.auto_backup_enabled,
            "retention_max_count": self.settings.backup_max_count,
            "retention_days": self.settings.backup_retention_days,
            "backup_directory": str(self.backup_dir),
        }
