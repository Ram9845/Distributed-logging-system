"""
Cleanup script — remove old data, Docker volumes, and temp files.

Provides utilities for cleaning up the logging system:
- Delete old log entries from PostgreSQL
- Purge Docker volumes
- Clean up local temp files and logs

Usage:
    python -m scripts.cleanup [--days 7] [--dry-run]
"""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta

import psycopg2


def cleanup_old_logs(
    db_url: str, days: int, dry_run: bool = False
) -> int:
    """Delete log entries older than N days from PostgreSQL."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    print(f"  Cleaning logs older than {days} days (before {cutoff.isoformat()})...")

    conn = psycopg2.connect(db_url)

    with conn.cursor() as cur:
        # Count affected rows
        cur.execute(
            "SELECT COUNT(*) FROM logs WHERE timestamp < %s", (cutoff,)
        )
        count = cur.fetchone()[0]

        if dry_run:
            print(f"  [DRY RUN] Would delete {count} log entries.")
        else:
            cur.execute(
                "DELETE FROM logs WHERE timestamp < %s", (cutoff,)
            )
            conn.commit()
            print(f"  Deleted {count} log entries.")

        # Also clean old resolved alerts
        cur.execute(
            "SELECT COUNT(*) FROM alerts WHERE resolved = true AND triggered_at < %s",
            (cutoff,),
        )
        alert_count = cur.fetchone()[0]

        if not dry_run:
            cur.execute(
                "DELETE FROM alerts WHERE resolved = true AND triggered_at < %s",
                (cutoff,),
            )
            conn.commit()

        print(f"  {'Would delete' if dry_run else 'Deleted'} {alert_count} resolved alerts.")

    conn.close()
    return count


def cleanup_local_logs(dry_run: bool = False) -> int:
    """Remove local log files."""
    log_dir = "logs"
    removed = 0

    if os.path.exists(log_dir):
        for filename in os.listdir(log_dir):
            filepath = os.path.join(log_dir, filename)
            if os.path.isfile(filepath):
                if dry_run:
                    print(f"  [DRY RUN] Would remove: {filepath}")
                else:
                    os.remove(filepath)
                    print(f"  Removed: {filepath}")
                removed += 1

    return removed


def cleanup_docker_volumes(dry_run: bool = False) -> None:
    """Remove Docker compose volumes (requires confirmation)."""
    if dry_run:
        print("  [DRY RUN] Would run: docker compose down -v")
        return

    print("  This will remove ALL Docker volumes including databases!")
    confirm = input("  Are you sure? (yes/no): ").strip().lower()

    if confirm == "yes":
        subprocess.run(
            ["docker", "compose", "down", "-v", "--remove-orphans"],
            check=True,
        )
        print("  Docker volumes removed.")
    else:
        print("  Skipped Docker volume cleanup.")


def refresh_materialized_views(db_url: str, dry_run: bool = False) -> None:
    """Refresh PostgreSQL materialized views after cleanup."""
    if dry_run:
        print("  [DRY RUN] Would refresh materialized views.")
        return

    print("  Refreshing materialized views...")
    conn = psycopg2.connect(db_url)
    with conn.cursor() as cur:
        cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY service_log_stats")
        conn.commit()
    conn.close()
    print("  Materialized views refreshed.")


def main(days: int, dry_run: bool, db_url: str, include_docker: bool) -> None:
    """Run all cleanup tasks."""
    print(f"\n{'='*60}")
    print(f"  Distributed Logging System — Cleanup")
    print(f"  {'[DRY RUN] ' if dry_run else ''}Retention: {days} days")
    print(f"{'='*60}\n")

    # 1. Clean old database logs
    print("[1/4] Database Cleanup")
    try:
        cleanup_old_logs(db_url, days, dry_run)
    except Exception as e:
        print(f"  WARNING: Database cleanup failed: {e}")

    # 2. Refresh views
    print("\n[2/4] Refresh Materialized Views")
    try:
        refresh_materialized_views(db_url, dry_run)
    except Exception as e:
        print(f"  WARNING: View refresh failed: {e}")

    # 3. Clean local logs
    print("\n[3/4] Local Log Files")
    removed = cleanup_local_logs(dry_run)
    print(f"  {removed} files {'would be' if dry_run else ''} removed.")

    # 4. Docker volumes (optional)
    print("\n[4/4] Docker Volumes")
    if include_docker:
        cleanup_docker_volumes(dry_run)
    else:
        print("  Skipped (use --docker to include).")

    print(f"\n{'='*60}")
    print(f"  Cleanup {'simulation' if dry_run else 'complete'}!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup old logs and data")
    parser.add_argument("--days", type=int, default=7, help="Delete logs older than N days")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    parser.add_argument("--docker", action="store_true", help="Also remove Docker volumes")
    parser.add_argument(
        "--db-url",
        default="postgresql://loguser:logpassword123@localhost:5432/logging_db",
        help="PostgreSQL connection URL",
    )
    args = parser.parse_args()

    main(args.days, args.dry_run, args.db_url, args.docker)
