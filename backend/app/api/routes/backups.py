"""LedgerLens API endpoints for database backup and restore management.

Endpoints:
- GET /api/backups: List backups and diagnostic summary
- POST /api/backups: Create a manual database backup
- GET /api/backups/diagnostics: Operational & financial data metrics
- GET /api/backups/{backup_id}: Get backup metadata
- POST /api/backups/{backup_id}/verify: Verify backup integrity
- POST /api/backups/{backup_id}/restore: Restore database from backup
- DELETE /api/backups/{backup_id}: Delete a backup
- POST /api/backups/prune: Prune backups based on retention policies
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.backup_service import BackupMetadata, BackupService


router = APIRouter(prefix="/api/backups", tags=["Backups"])


def get_backup_service() -> BackupService:
    """Dependency provider for BackupService."""
    return BackupService()


class CreateBackupRequest(BaseModel):
    """Request payload for creating a backup."""
    backup_type: str = Field(default="manual", description="Type: manual or scheduled")


class RestoreBackupRequest(BaseModel):
    """Request payload for restoring a backup."""
    confirm: bool = Field(..., description="Must explicitly be True to confirm data replacement")


class VerifyBackupRequest(BaseModel):
    """Request payload for verifying a backup."""
    test_restore: bool = Field(default=False, description="Run test restore into isolated test DB")


@router.get("", response_model=Dict[str, Any], summary="List backups and summary")
def list_backups(
    service: BackupService = Depends(get_backup_service),
) -> Dict[str, Any]:
    """Retrieve all available backups and operational storage diagnostics."""
    backups = [b.to_dict() for b in service.list_backups()]
    diagnostics = service.get_diagnostics()
    return {
        "backups": backups,
        "diagnostics": diagnostics,
    }


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create database backup")
def create_backup(
    payload: CreateBackupRequest = CreateBackupRequest(),
    service: BackupService = Depends(get_backup_service),
) -> Dict[str, Any]:
    """Create a new timestamped database backup."""
    try:
        meta = service.create_backup(backup_type=payload.backup_type)
        return {
            "message": "Database backup created successfully.",
            "backup": meta.to_dict(),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup creation failed: {exc}",
        )


@router.get("/diagnostics", summary="Get operational diagnostics")
def get_diagnostics(
    service: BackupService = Depends(get_backup_service),
) -> Dict[str, Any]:
    """Return database connection status, table row counts, and storage metrics."""
    return service.get_diagnostics()


@router.get("/{backup_id}", summary="Get backup details")
def get_backup(
    backup_id: str,
    service: BackupService = Depends(get_backup_service),
) -> Dict[str, Any]:
    """Retrieve metadata for a specific backup by identifier."""
    try:
        meta = service.get_backup_metadata(backup_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if not meta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    return meta.to_dict()


@router.post("/{backup_id}/verify", summary="Verify backup integrity")
def verify_backup(
    backup_id: str,
    payload: VerifyBackupRequest = VerifyBackupRequest(),
    service: BackupService = Depends(get_backup_service),
) -> Dict[str, Any]:
    """Check checksum and SQL format validity of a backup."""
    try:
        result = service.verify_backup(backup_id, test_isolated_restore=payload.test_restore)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/{backup_id}/restore", summary="Restore database from backup")
def restore_backup(
    backup_id: str,
    payload: RestoreBackupRequest,
    service: BackupService = Depends(get_backup_service),
) -> Dict[str, Any]:
    """Restore the database from a verified backup.

    Requires confirm=True. An automatic safety backup will be created first.
    """
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation is required to perform a restore operation.",
        )

    try:
        result = service.restore_backup(backup_id, confirmation=True)
        return {
            "message": "Database restored successfully.",
            "details": result,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Restore operation failed: {exc}",
        )


@router.delete("/{backup_id}", summary="Delete a backup")
def delete_backup(
    backup_id: str,
    service: BackupService = Depends(get_backup_service),
) -> Dict[str, Any]:
    """Delete a backup file and its companion metadata."""
    try:
        deleted = service.delete_backup(backup_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
        return {"message": "Backup deleted successfully.", "backup_id": backup_id}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/prune", summary="Apply retention policy")
def prune_backups(
    service: BackupService = Depends(get_backup_service),
) -> Dict[str, Any]:
    """Prune old backups according to retention policies."""
    result = service.prune_backups()
    return {
        "message": f"Pruned {result['pruned_count']} old backup(s).",
        "result": result,
    }
