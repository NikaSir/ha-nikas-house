"""Synchronize bundled public contracts/manifests/navigation into the runtime source tree."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PUBLIC_SOURCE_DIRECTORIES = ("contracts", "manifests", "navigation")


@dataclass(frozen=True, slots=True)
class SourceSyncResult:
    """Result of synchronizing packaged public sources."""

    changed_files: int
    checked_files: int


def _atomic_sync(source: Path, target: Path) -> bool:
    payload = source.read_bytes()
    if target.exists() and target.read_bytes() == payload:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f".{target.name}.tmp")
    temp.write_bytes(payload)
    os.replace(temp, target)
    return True


def sync_bundled_public_sources(source_root: Path) -> SourceSyncResult:
    """Sync only the bundled House contract, manifest and navigation sources."""
    bundled_root = Path(__file__).with_name("bundled_sources")
    changed = 0
    checked = 0
    for directory in PUBLIC_SOURCE_DIRECTORIES:
        packaged = bundled_root / directory
        if not packaged.exists():
            continue
        for source in sorted(packaged.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(packaged)
            target = source_root / directory / relative
            checked += 1
            changed += int(_atomic_sync(source, target))
    return SourceSyncResult(changed_files=changed, checked_files=checked)
