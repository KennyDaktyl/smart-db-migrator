#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from dotenv import load_dotenv
from sqlalchemy import create_engine

ROOT_DIR = Path(__file__).resolve().parents[1]
SMART_COMMON_DIR = ROOT_DIR / "smart_common"
MIGRATIONS_DIR = ROOT_DIR / "migrations"
ALEMBIC_INI_PATH = ROOT_DIR / "alembic.ini"

ENV_TO_DB_VAR = {
    "dev": "DB_URL_DEV",
    "prod": "DB_URL_PROD",
}


def bootstrap() -> None:
    load_dotenv(ROOT_DIR / ".env")

    # smart_common settings expect these values even if migrations only need DB URL.
    os.environ.setdefault("POSTGRES_PASSWORD", "placeholder")
    os.environ.setdefault("JWT_SECRET", "placeholder")
    os.environ.setdefault("FERNET_KEY", "placeholder")
    os.environ.setdefault("EMAIL_HOST", "localhost")
    os.environ.setdefault("EMAIL_FROM", "no-reply@localhost")

    sys.path.insert(0, str(ROOT_DIR))

    if not SMART_COMMON_DIR.exists():
        raise SystemExit("Missing smart_common submodule. Run: git submodule update --init --recursive")

    # Avoid executing heavy providers package __init__ when models import provider enums.
    if "smart_common.providers" not in sys.modules:
        providers_pkg = types.ModuleType("smart_common.providers")
        providers_pkg.__path__ = [str(SMART_COMMON_DIR / "providers")]
        sys.modules["smart_common.providers"] = providers_pkg


bootstrap()

import smart_common.models  # noqa: F401,E402
from smart_common.core.db import Base  # noqa: E402


def _database_url(target_env: str) -> str:
    env_var = ENV_TO_DB_VAR[target_env]
    url = os.getenv(env_var)
    if not url:
        raise SystemExit(f"Missing {env_var} in .env")
    return url


def _config(target_env: str) -> tuple[Config, str]:
    script_location = MIGRATIONS_DIR / target_env
    if not script_location.exists():
        raise SystemExit(f"Missing migration directory: {script_location}")

    database_url = _database_url(target_env)
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(script_location))
    config.set_main_option("prepend_sys_path", str(ROOT_DIR))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    config.set_main_option("target_env", target_env)
    return config, database_url


def _has_schema_changes(database_url: str) -> bool:
    engine = create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(
                connection=connection,
                opts={"compare_type": True, "compare_server_default": True},
            )
            return bool(compare_metadata(context, Base.metadata))
    finally:
        engine.dispose()


def _db_is_at_head(database_url: str, config: Config) -> bool:
    script = ScriptDirectory.from_config(config)
    expected_heads = set(script.get_heads())
    if not expected_heads:
        return True

    engine = create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_heads = set(context.get_current_heads())
    finally:
        engine.dispose()

    return current_heads == expected_heads


def _migration_message(message: str | None) -> str:
    if message:
        return message
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"auto migration {timestamp}"


def _latest_or_selected_revision_file(directory: Path, revision: str | None) -> Path:
    files = sorted(directory.glob("*.py"), key=lambda item: item.stat().st_mtime)
    if not files:
        raise SystemExit(f"No migration files in {directory}")

    if revision is None:
        return files[-1]

    matches = [item for item in files if item.name.startswith(f"{revision}_")]
    if not matches:
        raise SystemExit(f"Cannot find revision '{revision}' in {directory}")
    if len(matches) > 1:
        raise SystemExit(f"Revision prefix '{revision}' is ambiguous in {directory}")
    return matches[0]


def cmd_create(args: argparse.Namespace) -> int:
    config, database_url = _config(args.env)
    if not _has_schema_changes(database_url):
        logging.info("No schema changes detected for %s.", args.env)
        return 0

    if not _db_is_at_head(database_url, config):
        logging.error("Database %s is not at migration HEAD. Run apply first.", args.env)
        return 1

    command.revision(config, autogenerate=True, message=_migration_message(args.message))
    logging.info("Created migration for %s.", args.env)
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    config, _ = _config(args.env)
    command.upgrade(config, args.revision)
    logging.info("Applied migrations for %s up to %s.", args.env, args.revision)
    return 0


def cmd_current(args: argparse.Namespace) -> int:
    config, _ = _config(args.env)
    command.current(config, verbose=args.verbose)
    return 0


def cmd_heads(args: argparse.Namespace) -> int:
    config, _ = _config(args.env)
    command.heads(config, verbose=args.verbose)
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    config, _ = _config(args.env)
    command.history(config, rev_range=args.rev_range, verbose=args.verbose)
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    source_dir = MIGRATIONS_DIR / "dev" / "versions"
    target_dir = MIGRATIONS_DIR / "prod" / "versions"

    source_file = _latest_or_selected_revision_file(source_dir, args.revision)
    target_file = target_dir / source_file.name

    if target_file.exists() and not args.force:
        raise SystemExit(f"{target_file.name} already exists in prod. Use --force to overwrite.")

    shutil.copy2(source_file, target_file)
    logging.info("Promoted %s -> %s", source_file.name, target_file.name)
    return 0


def cmd_models_diff(args: argparse.Namespace) -> int:
    command_args = [
        "git",
        "-C",
        str(SMART_COMMON_DIR),
        "diff",
        "--name-status",
        f"{args.base}..HEAD",
        "--",
        "models",
    ]

    result = subprocess.run(command_args, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(result.stderr.strip() or "Failed to read smart_common/models diff.")
        return result.returncode

    output = result.stdout.strip()
    if output:
        print(output)
    else:
        print(f"No changes in smart_common/models for {args.base}..HEAD")
    return 0


def _add_env_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--env", choices=("dev", "prod"), required=True, help="Target environment.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage Alembic migrations for smart_common with separate dev/prod histories."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Autogenerate migration for selected environment.")
    _add_env_argument(create_parser)
    create_parser.add_argument("-m", "--message", help="Optional migration message.")
    create_parser.set_defaults(func=cmd_create)

    apply_parser = subparsers.add_parser("apply", help="Apply migrations for selected environment.")
    _add_env_argument(apply_parser)
    apply_parser.add_argument(
        "--revision",
        default="head",
        help="Target revision for upgrade (default: head).",
    )
    apply_parser.set_defaults(func=cmd_apply)

    current_parser = subparsers.add_parser("current", help="Show current DB revision.")
    _add_env_argument(current_parser)
    current_parser.add_argument("--verbose", action="store_true", help="Show detailed output.")
    current_parser.set_defaults(func=cmd_current)

    heads_parser = subparsers.add_parser("heads", help="Show heads from migration directory.")
    _add_env_argument(heads_parser)
    heads_parser.add_argument("--verbose", action="store_true", help="Show detailed output.")
    heads_parser.set_defaults(func=cmd_heads)

    history_parser = subparsers.add_parser("history", help="Show migration history.")
    _add_env_argument(history_parser)
    history_parser.add_argument("--verbose", action="store_true", help="Show detailed output.")
    history_parser.add_argument("--rev-range", help="Alembic revision range, e.g. base:head.")
    history_parser.set_defaults(func=cmd_history)

    promote_parser = subparsers.add_parser(
        "promote", help="Copy a migration from dev versions to prod versions."
    )
    promote_parser.add_argument(
        "--revision",
        help="Revision prefix to promote. If omitted, latest dev migration is used.",
    )
    promote_parser.add_argument("--force", action="store_true", help="Overwrite existing file in prod.")
    promote_parser.set_defaults(func=cmd_promote)

    models_diff_parser = subparsers.add_parser(
        "models-diff", help="Show changed files in smart_common/models for selected base ref."
    )
    models_diff_parser.add_argument(
        "--base",
        default="origin/develop",
        help="Git ref to compare against (default: origin/develop).",
    )
    models_diff_parser.set_defaults(func=cmd_models_diff)

    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
