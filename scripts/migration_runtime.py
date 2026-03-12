from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path

from dotenv import load_dotenv


def resolve_smart_common_dir(root_dir: Path) -> Path:
    explicit_path = os.getenv("SMART_COMMON_PATH")
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path).expanduser())

    candidates.extend(
        [
            root_dir / "smart_common",
            root_dir.parent / "smart-common",
            root_dir.parent / "smart_common",
        ]
    )

    for candidate in candidates:
        resolved = candidate.resolve()
        if (resolved / "__init__.py").exists() and (resolved / "models").is_dir():
            return resolved

    raise SystemExit(
        "Cannot locate smart-common sources. Set SMART_COMMON_PATH or provide "
        "smart_common submodule / ../smart-common checkout."
    )


def bootstrap_runtime(root_dir: Path) -> Path:
    load_dotenv(root_dir / ".env")

    os.environ.setdefault("POSTGRES_PASSWORD", "placeholder")
    os.environ.setdefault("JWT_SECRET", "placeholder")
    os.environ.setdefault("FERNET_KEY", "placeholder")
    os.environ.setdefault("EMAIL_HOST", "localhost")
    os.environ.setdefault("EMAIL_FROM", "no-reply@localhost")

    smart_common_dir = resolve_smart_common_dir(root_dir)
    smart_common_parent = smart_common_dir.parent

    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    if str(smart_common_parent) not in sys.path:
        sys.path.insert(0, str(smart_common_parent))

    if "smart_common" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "smart_common",
            smart_common_dir / "__init__.py",
            submodule_search_locations=[str(smart_common_dir)],
        )
        if spec is None or spec.loader is None:
            raise SystemExit(f"Cannot bootstrap smart_common package from {smart_common_dir}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["smart_common"] = module
        spec.loader.exec_module(module)

    if "smart_common.providers" not in sys.modules:
        providers_pkg = types.ModuleType("smart_common.providers")
        providers_pkg.__path__ = [str(smart_common_dir / "providers")]
        sys.modules["smart_common.providers"] = providers_pkg

    return smart_common_dir
