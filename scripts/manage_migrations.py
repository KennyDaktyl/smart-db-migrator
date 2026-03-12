#!/usr/bin/env python3
from __future__ import annotations

import ast
import argparse
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

ROOT_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT_DIR / "migrations"
ALEMBIC_INI_PATH = ROOT_DIR / "alembic.ini"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.migration_runtime import bootstrap_runtime

ENV_TO_DB_VAR = {
    "dev": "DB_URL_DEV",
    "prod": "DB_URL_PROD",
}

SMART_COMMON_DIR = bootstrap_runtime(ROOT_DIR)

import smart_common.models  # noqa: F401,E402
from smart_common.core.db import Base  # noqa: E402


def _database_url(target_env: str) -> str:
    env_var = ENV_TO_DB_VAR[target_env]
    url = os.getenv(env_var)
    if not url:
        raise SystemExit(f"Missing {env_var} in .env")
    return url


def _config(target_env: str, *, require_database_url: bool = True) -> tuple[Config, str | None]:
    script_location = MIGRATIONS_DIR / target_env
    if not script_location.exists():
        raise SystemExit(f"Missing migration directory: {script_location}")

    database_url = _database_url(target_env) if require_database_url else os.getenv(
        ENV_TO_DB_VAR[target_env]
    )
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(script_location))
    config.set_main_option("prepend_sys_path", str(ROOT_DIR))
    if database_url:
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


def _archive_migration_files(target_env: str, files: list[Path]) -> None:
    if not files:
        return

    archive_dir = MIGRATIONS_DIR / target_env / "versions_archive" / datetime.now(timezone.utc).strftime("%Y/%m")
    archive_dir.mkdir(parents=True, exist_ok=True)

    for migration_file in files:
        shutil.copy2(migration_file, archive_dir / migration_file.name)

    logging.info(
        "Archived %d migration file(s) for %s in %s.",
        len(files),
        target_env,
        archive_dir,
    )


def _collect_added_column_enums(migration_file: Path) -> list[tuple[str, tuple[str, ...]]]:
    source = migration_file.read_text(encoding="utf-8")
    module = ast.parse(source)

    upgrade_fn: ast.FunctionDef | None = None
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "upgrade":
            upgrade_fn = node
            break

    if upgrade_fn is None:
        return []

    collected: list[tuple[str, tuple[str, ...]]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()

    for node in ast.walk(upgrade_fn):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_column":
            continue

        for arg in node.args:
            if not isinstance(arg, ast.Call):
                continue
            if not isinstance(arg.func, ast.Attribute) or arg.func.attr != "Column":
                continue

            for col_arg in arg.args:
                if not isinstance(col_arg, ast.Call):
                    continue
                if not isinstance(col_arg.func, ast.Attribute) or col_arg.func.attr != "Enum":
                    continue

                enum_values: list[str] = []
                for enum_arg in col_arg.args:
                    if isinstance(enum_arg, ast.Constant) and isinstance(enum_arg.value, str):
                        enum_values.append(enum_arg.value)

                name_value: str | None = None
                for kw in col_arg.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        name_value = kw.value.value
                        break

                if not enum_values or not name_value:
                    continue

                key = (name_value, tuple(enum_values))
                if key not in seen:
                    seen.add(key)
                    collected.append(key)

    return collected


def _var_name_from_enum_name(enum_name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in enum_name.strip().lower()).strip("_")
    if not cleaned:
        cleaned = "enum_type"
    if cleaned[0].isdigit():
        cleaned = f"enum_{cleaned}"
    return cleaned


def _add_enum_create_drop_to_migration(migration_file: Path) -> bool:
    enum_defs = _collect_added_column_enums(migration_file)
    if not enum_defs:
        return False

    original = migration_file.read_text(encoding="utf-8")
    if "op.get_bind()" in original and ".create(bind, checkfirst=True)" in original:
        return False

    lines = original.splitlines()

    module = ast.parse(original)
    functions = {
        node.name: node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name in {"upgrade", "downgrade"}
    }
    upgrade_fn = functions.get("upgrade")
    downgrade_fn = functions.get("downgrade")
    if upgrade_fn is None or downgrade_fn is None:
        return False

    def _find_marker_line(start: int, marker: str, end: int | None = None) -> int | None:
        upper_bound = len(lines) if end is None else min(end, len(lines))
        for idx in range(start, upper_bound):
            if marker in lines[idx]:
                return idx
        return None

    upgrade_start = upgrade_fn.lineno - 1
    downgrade_start = downgrade_fn.lineno - 1

    upgrade_marker = _find_marker_line(
        upgrade_start,
        "# ### commands auto generated by Alembic - please adjust! ###",
        end=downgrade_start + 1,
    )
    downgrade_end_marker = _find_marker_line(
        downgrade_start,
        "# ### end Alembic commands ###",
    )

    if upgrade_marker is None or downgrade_end_marker is None:
        return False

    bind_create_lines = ["    bind = op.get_bind()"]
    bind_drop_lines = ["    bind = op.get_bind()"]

    for enum_name, enum_values in enum_defs:
        enum_values_str = ", ".join(repr(value) for value in enum_values)
        var_name = _var_name_from_enum_name(enum_name)
        bind_create_lines.append(f"    {var_name} = sa.Enum({enum_values_str}, name={enum_name!r})")
        bind_create_lines.append(f"    {var_name}.create(bind, checkfirst=True)")
        bind_drop_lines.append(f"    {var_name} = sa.Enum({enum_values_str}, name={enum_name!r})")
        bind_drop_lines.append(f"    {var_name}.drop(bind, checkfirst=True)")

    # Insert create statements right after the autogenerated marker in upgrade()
    lines = lines[: upgrade_marker + 1] + bind_create_lines + lines[upgrade_marker + 1 :]
    shift = len(bind_create_lines)

    # Recompute marker for downgrade() after first insertion shifted line numbers.
    shifted_downgrade_start = downgrade_start + shift
    downgrade_end_marker = _find_marker_line(shifted_downgrade_start, "# ### end Alembic commands ###")
    if downgrade_end_marker is None:
        return False

    # Insert drop statements right before the end marker in downgrade()
    lines = lines[:downgrade_end_marker] + bind_drop_lines + lines[downgrade_end_marker:]

    updated = "\n".join(lines) + "\n"
    migration_file.write_text(updated, encoding="utf-8")
    return True


def cmd_create(args: argparse.Namespace) -> int:
    config, database_url = _config(args.env)
    if not _has_schema_changes(database_url):
        logging.info("No schema changes detected for %s.", args.env)
        return 0

    if not _db_is_at_head(database_url, config):
        logging.error("Database %s is not at migration HEAD. Run apply first.", args.env)
        return 1

    versions_dir = MIGRATIONS_DIR / args.env / "versions"
    before_create = {item.name for item in versions_dir.glob("*.py")}
    command.revision(config, autogenerate=True, message=_migration_message(args.message))
    after_create = {item.name for item in versions_dir.glob("*.py")}
    created_files = sorted((versions_dir / name for name in (after_create - before_create)), key=lambda item: item.name)

    if args.archive:
        _archive_migration_files(args.env, created_files)

    patched_files = [file for file in created_files if _add_enum_create_drop_to_migration(file)]
    if patched_files:
        for file in patched_files:
            logging.info("Added explicit PostgreSQL enum create/drop to %s.", file.name)

    logging.info("Created migration for %s.", args.env)
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    config, _ = _config(args.env)
    command.upgrade(config, args.revision)
    logging.info("Applied migrations for %s up to %s.", args.env, args.revision)
    return 0


def cmd_stamp(args: argparse.Namespace) -> int:
    config, _ = _config(args.env)
    command.stamp(config, args.revision)
    logging.info("Stamped %s database to %s.", args.env, args.revision)
    return 0


def cmd_current(args: argparse.Namespace) -> int:
    config, _ = _config(args.env)
    command.current(config, verbose=args.verbose)
    return 0


def cmd_heads(args: argparse.Namespace) -> int:
    config, _ = _config(args.env, require_database_url=False)
    command.heads(config, verbose=args.verbose)
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    config, _ = _config(args.env, require_database_url=False)
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
        description="Manage Alembic migrations from smart-common SQLAlchemy models with separate dev/prod histories."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Autogenerate migration for selected environment.")
    _add_env_argument(create_parser)
    create_parser.add_argument("-m", "--message", help="Optional migration message.")
    create_parser.add_argument(
        "--archive",
        action="store_true",
        help="Copy created migration to versions_archive (disabled by default).",
    )
    create_parser.set_defaults(func=cmd_create)

    apply_parser = subparsers.add_parser("apply", help="Apply migrations for selected environment.")
    _add_env_argument(apply_parser)
    apply_parser.add_argument(
        "--revision",
        default="head",
        help="Target revision for upgrade (default: head).",
    )
    apply_parser.set_defaults(func=cmd_apply)

    stamp_parser = subparsers.add_parser(
        "stamp",
        help="Set DB revision without running migrations (advanced).",
    )
    _add_env_argument(stamp_parser)
    stamp_parser.add_argument(
        "--revision",
        required=True,
        help="Revision to stamp, e.g. head or exact revision ID.",
    )
    stamp_parser.set_defaults(func=cmd_stamp)

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
