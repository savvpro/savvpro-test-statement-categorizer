"""LedgerLens Command-Line Interface for Database Backup, Restore, and Maintenance.

Supports OS-level cron jobs, scheduled tasks, and administrative maintenance.

Usage:
    python backup_cli.py create [--type manual|scheduled]
    python backup_cli.py list
    python backup_cli.py verify <backup_id>
    python backup_cli.py restore <backup_id> --confirm
    python backup_cli.py prune
    python backup_cli.py diagnostics
"""

import argparse
import json
import sys

from app.core.config import get_settings
from app.services.backup_service import BackupService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LedgerLens Backup, Restore, and Data Management CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. create
    create_parser = subparsers.add_parser("create", help="Create a database backup")
    create_parser.add_argument(
        "--type",
        dest="backup_type",
        choices=["manual", "scheduled"],
        default="manual",
        help="Type of backup (manual or scheduled)",
    )

    # 2. list
    subparsers.add_parser("list", help="List all available backups")

    # 3. verify
    verify_parser = subparsers.add_parser("verify", help="Verify backup checksum and format")
    verify_parser.add_argument("backup_id", help="Identifier of backup to verify")
    verify_parser.add_argument(
        "--test-restore",
        action="store_true",
        help="Execute test restoration into isolated test database",
    )

    # 4. restore
    restore_parser = subparsers.add_parser("restore", help="Restore database from backup")
    restore_parser.add_argument("backup_id", help="Identifier of backup to restore")
    restore_parser.add_argument(
        "--confirm",
        action="store_true",
        required=True,
        help="Explicit confirmation that existing database data will be overwritten",
    )

    # 5. prune
    subparsers.add_parser("prune", help="Prune old backups according to retention policies")

    # 6. diagnostics
    subparsers.add_parser("diagnostics", help="Show database connection and backup diagnostics")

    args = parser.parse_args()
    service = BackupService()

    try:
        if args.command == "create":
            print(f"Creating {args.backup_type} backup...")
            meta = service.create_backup(backup_type=args.backup_type)
            print("Backup created successfully:")
            print(f"  ID:         {meta.backup_id}")
            print(f"  Filename:   {meta.filename}")
            print(f"  Size:       {meta.file_size_bytes} bytes")
            print(f"  Checksum:   {meta.sha256_checksum}")
            print(f"  Status:     {meta.status} ({meta.verification_status})")

        elif args.command == "list":
            backups = service.list_backups()
            if not backups:
                print("No backups found.")
                return

            print(f"{'BACKUP ID':<40} {'CREATED (UTC)':<20} {'SIZE':<12} {'TYPE':<10} {'STATUS':<10} {'VERIFIED':<15}")
            print("-" * 110)
            for b in backups:
                created = b.created_at[:19].replace("T", " ")
                size_str = (
                    f"{b.file_size_bytes / 1048576:.2f} MB"
                    if b.file_size_bytes >= 1048576
                    else f"{b.file_size_bytes / 1024:.1f} KB"
                )
                print(
                    f"{b.backup_id:<40} {created:<20} {size_str:<12} {b.backup_type:<10} {b.status:<10} {b.verification_status:<15}"
                )

        elif args.command == "verify":
            print(f"Verifying backup '{args.backup_id}'...")
            res = service.verify_backup(args.backup_id, test_isolated_restore=args.test_restore)
            if res.get("valid"):
                print("Verification PASSED:")
                print(f"  Status:   {res.get('verification_status')}")
                print(f"  Checksum: {res.get('sha256_checksum')}")
                print(f"  Size:     {res.get('file_size_bytes')} bytes")
            else:
                print("Verification FAILED:")
                print(f"  Reason:   {res.get('reason')}")
                sys.exit(1)

        elif args.command == "restore":
            print(f"Initiating restore from '{args.backup_id}'...")
            print("Creating mandatory pre-restore safety backup...")
            res = service.restore_backup(args.backup_id, confirmation=args.confirm)
            print("Restore COMPLETED successfully:")
            print(f"  Restored Backup: {res.get('restored_backup_id')}")
            print(f"  Safety Backup:   {res.get('safety_backup_id')}")
            print(f"  Elapsed Time:    {res.get('elapsed_seconds')}s")
            print(f"  Table Counts:    {json.dumps(res.get('table_counts', {}))}")

        elif args.command == "prune":
            print("Applying backup retention policies...")
            res = service.prune_backups()
            print("Retention pruning complete:")
            print(f"  Pruned:   {res.get('pruned_count')} backup(s)")
            if res.get("pruned_ids"):
                print(f"  Removed:  {', '.join(res.get('pruned_ids'))}")
            print(f"  Retained: {res.get('retained_count')} backup(s)")

        elif args.command == "diagnostics":
            diag = service.get_diagnostics()
            print("LedgerLens Operational & Backup Diagnostics:")
            print(f"  Database Status:        {'Connected' if diag['database_connected'] else 'Disconnected'}")
            print(f"  Database Target:        {diag['database_masked_url']}")
            print(f"  Record Counts:          {json.dumps(diag['table_counts'])}")
            print(f"  Total Backups:          {diag['total_backups_count']} ({diag['total_size_formatted']})")
            print(f"  Last Successful Backup: {diag['last_successful_backup']['backup_id'] if diag['last_successful_backup'] else 'None'}")
            print(f"  Days Since Last Backup: {diag['days_since_last_backup']}")
            if diag.get("backup_warning"):
                print(f"  Warning:                {diag['backup_warning']}")
            print(f"  Auto Backups Config:    {'Enabled' if diag['auto_backup_enabled'] else 'Disabled'}")
            print(f"  Retention Limits:       Max {diag['retention_max_count']} backups, {diag['retention_days']} days")
            print(f"  Backup Storage Path:    {diag['backup_directory']}")

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
