#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BACKUP_ROOT = ROOT_DIR / "backups"
ENV_TO_DB_VAR = {
    "dev": "DB_URL_DEV",
    "prod": "DB_URL_PROD",
}


def _load_env() -> None:
    load_dotenv(ROOT_DIR / ".env")


def _db_url(target_env: str) -> str:
    env_var = ENV_TO_DB_VAR[target_env]
    url = os.getenv(env_var)
    if not url:
        raise SystemExit(f"Missing {env_var} in .env")
    return url


def _connection_parts(target_env: str) -> dict[str, str | None]:
    url = _db_url(target_env)
    parsed = make_url(url)

    if not parsed.drivername.startswith("postgresql"):
        raise SystemExit(f"{ENV_TO_DB_VAR[target_env]} must point to PostgreSQL database.")

    if not parsed.database:
        raise SystemExit(f"{ENV_TO_DB_VAR[target_env]} has no database name.")

    return {
        "host": parsed.host or "localhost",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "postgres",
        "password": parsed.password,
        "database": parsed.database,
    }


def _base_env(password: str | None) -> dict[str, str]:
    env = os.environ.copy()
    if password is not None:
        env["PGPASSWORD"] = password
    return env


def _run(command: list[str], env: dict[str, str]) -> None:
    subprocess.run(command, check=True, env=env)


def _db_client_args(parts: dict[str, str | None]) -> list[str]:
    return [
        "-h",
        str(parts["host"]),
        "-p",
        str(parts["port"]),
        "-U",
        str(parts["user"]),
        "-d",
        str(parts["database"]),
    ]


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")


def _date_dir() -> str:
    return datetime.now(timezone.utc).strftime("%Y/%m")


def _backup_one(
    target_env: str,
    output_root: Path,
    fmt: str,
    verify: bool,
    upload_remote: str | None,
) -> Path:
    parts = _connection_parts(target_env)
    out_dir = output_root / _date_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    suffix = "dump" if fmt == "custom" else "sql"
    out_path = out_dir / f"{target_env}_{_timestamp()}.{suffix}"

    command = [
        "pg_dump",
        *_db_client_args(parts),
        "--no-owner",
        "--no-privileges",
        "--format",
        "custom" if fmt == "custom" else "plain",
        "--file",
        str(out_path),
    ]
    env = _base_env(parts["password"])
    _run(command, env=env)

    if verify and fmt == "custom":
        _run(["pg_restore", "--list", str(out_path)], env=env)

    if upload_remote:
        remote_target = f"{upload_remote.rstrip('/')}/{_date_dir()}"
        _run(["rclone", "copy", str(out_path), remote_target], env=env)

    return out_path


def _cleanup_old_backups(output_root: Path, retention_days: int) -> None:
    if retention_days < 0:
        return

    now = datetime.now(timezone.utc).timestamp()
    max_age_seconds = retention_days * 24 * 3600
    for backup_file in output_root.rglob("*"):
        if not backup_file.is_file():
            continue
        if backup_file.suffix not in (".dump", ".sql"):
            continue
        age_seconds = now - backup_file.stat().st_mtime
        if age_seconds > max_age_seconds:
            backup_file.unlink()


def cmd_backup(args: argparse.Namespace) -> int:
    _load_env()
    output_root = Path(args.output_root).resolve()
    envs = ["dev", "prod"] if args.env == "all" else [args.env]

    for target_env in envs:
        out_path = _backup_one(
            target_env=target_env,
            output_root=output_root,
            fmt=args.format,
            verify=args.verify,
            upload_remote=args.upload_remote,
        )
        print(f"OK backup {target_env}: {out_path}")

    _cleanup_old_backups(output_root, args.retention_days)
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    _load_env()
    target_file = Path(args.file).resolve()
    if not target_file.exists():
        raise SystemExit(f"Backup file not found: {target_file}")

    parts = _connection_parts(args.env)
    env = _base_env(parts["password"])

    if target_file.suffix == ".sql":
        command = [
            "psql",
            *_db_client_args(parts),
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            str(target_file),
        ]
        _run(command, env=env)
        print(f"OK restore {args.env} from SQL: {target_file}")
        return 0

    command = [
        "pg_restore",
        *_db_client_args(parts),
        "--no-owner",
        "--no-privileges",
    ]
    if args.clean:
        command.extend(["--clean", "--if-exists"])
    command.append(str(target_file))
    _run(command, env=env)
    print(f"OK restore {args.env} from dump: {target_file}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    _load_env()
    envs = ["dev", "prod"] if args.env == "all" else [args.env]

    for target_env in envs:
        parts = _connection_parts(target_env)
        env = _base_env(parts["password"])
        command = [
            "psql",
            *_db_client_args(parts),
            "-c",
            "select current_database(), current_user;",
        ]
        print(f"Checking {target_env}...")
        _run(command, env=env)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backup/restore utilities for smart-db-migrator.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup_parser = subparsers.add_parser("backup", help="Create DB backup for dev/prod/all.")
    backup_parser.add_argument("--env", choices=("dev", "prod", "all"), default="all")
    backup_parser.add_argument("--output-root", default=str(DEFAULT_BACKUP_ROOT))
    backup_parser.add_argument("--format", choices=("custom", "sql"), default="custom")
    backup_parser.add_argument("--retention-days", type=int, default=14)
    backup_parser.add_argument("--no-verify", action="store_false", dest="verify")
    backup_parser.add_argument("--upload-remote", help="Optional rclone remote, e.g. gdrive:smart-db-migrator")
    backup_parser.set_defaults(verify=True, func=cmd_backup)

    restore_parser = subparsers.add_parser("restore", help="Restore DB from .dump or .sql backup.")
    restore_parser.add_argument("--env", choices=("dev", "prod"), required=True)
    restore_parser.add_argument("--file", required=True, help="Path to backup file.")
    restore_parser.add_argument("--no-clean", action="store_false", dest="clean")
    restore_parser.set_defaults(clean=True, func=cmd_restore)

    check_parser = subparsers.add_parser("check", help="Test DB connectivity for env.")
    check_parser.add_argument("--env", choices=("dev", "prod", "all"), default="all")
    check_parser.set_defaults(func=cmd_check)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
