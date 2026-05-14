from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

from .config import PROJECT_ROOT


HASH_FILE_SUFFIXES = {".py", ".ps1", ".txt", ".json"}
HASH_DIRS = ("web_v1/agent", "web_v1/backend", "web_v1/deploy")
HASH_FILES = ("web_v1/VERSION",)


def _should_hash(path: Path) -> bool:
    name = path.name.lower()
    if not path.is_file():
        return False
    if "__pycache__" in path.parts:
        return False
    if ".backup_" in name or name.endswith((".bak", ".tmp", ".log", ".pyc", ".pyo")):
        return False
    return path.suffix.lower() in HASH_FILE_SUFFIXES


def _iter_bundle_files(project_root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in HASH_FILES:
        path = project_root / rel
        if path.is_file():
            files.append(path)
    for rel in HASH_DIRS:
        root = project_root / rel
        if not root.exists():
            continue
        files.extend(path for path in root.rglob("*") if _should_hash(path))
    return sorted(files, key=lambda path: path.relative_to(project_root).as_posix().lower())


@lru_cache(maxsize=1)
def expected_agent_bundle_hash() -> str:
    return compute_agent_bundle_hash(PROJECT_ROOT)


def compute_agent_bundle_hash(project_root: Path | None = None) -> str:
    root = Path(project_root or PROJECT_ROOT).resolve()
    digest = hashlib.sha256()
    for path in _iter_bundle_files(root):
        rel = path.relative_to(root).as_posix().lower()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
