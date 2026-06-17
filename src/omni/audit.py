"""Secret audit gate."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from omni.config import ensure_project_layout
from omni.redact import is_skiplisted_path, redact, redact_path


_STREAM_SCAN_CHUNK_BYTES = 512 * 1024
_STREAM_SCAN_OVERLAP_BYTES = 4096


@dataclass(frozen=True)
class AuditResult:
    ok: bool
    positive_failures: list[Path]
    negative_failures: list[Path]
    omni_leaks: list[Path]
    fixtures_missing: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "positive_failures": [str(path) for path in self.positive_failures],
            "negative_failures": [str(path) for path in self.negative_failures],
            "omni_leaks": [str(path) for path in self.omni_leaks],
            "fixtures_missing": self.fixtures_missing,
        }


def audit_secrets(root: Path | str, fixtures_root: Path | str | None = None) -> AuditResult:
    base = Path(root).resolve()
    fixture_base = Path(fixtures_root) if fixtures_root else _default_fixtures_root()
    allow_values = _load_allow_values(base)
    fixtures_missing = _fixtures_missing(fixture_base)
    planted_literals = _positive_fixture_literals(fixture_base, allow_values)

    positive_failures = _positive_failures(fixture_base, allow_values)
    negative_failures = _negative_failures(fixture_base, allow_values)
    omni_leaks = _omni_leaks(base, allow_values, planted_literals)
    ok = (
        not fixtures_missing
        and not positive_failures
        and not negative_failures
        and not omni_leaks
    )
    result = AuditResult(
        ok=ok,
        positive_failures=positive_failures,
        negative_failures=negative_failures,
        omni_leaks=omni_leaks,
        fixtures_missing=fixtures_missing,
    )
    marker = base / ".omni" / "audit" / "secrets.passed"
    if ok:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("ok\n", encoding="utf-8")
    elif marker.is_file():
        try:
            marker.unlink()
        except OSError:
            pass
    return result


def run_audit_cli(root: Path | str, fixtures_root: Path | str | None = None) -> tuple[int, str]:
    ensure_project_layout(root)
    result = audit_secrets(root, fixtures_root=fixtures_root)
    body = json.dumps(result.as_dict(), sort_keys=True, indent=2) + "\n"
    return (0 if result.ok else 1), body


def _default_fixtures_root() -> Path:
    return Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "redaction"


def _fixtures_missing(fixtures_root: Path) -> bool:
    positives = fixtures_root / "positives"
    negatives = fixtures_root / "negatives"
    return (
        not fixtures_root.is_dir()
        or not positives.is_dir()
        or not negatives.is_dir()
        or not _has_effective_fixture(positives)
        or not _has_effective_fixture(negatives)
    )


def _has_effective_fixture(directory: Path) -> bool:
    for path in directory.glob("*"):
        if path.is_file() and path.read_bytes().strip():
            return True
    return False


def _positive_failures(fixtures_root: Path, allow_values: set[str]) -> list[Path]:
    failures: list[Path] = []
    for path in sorted((fixtures_root / "positives").glob("*")):
        if not path.is_file():
            continue
        result = redact(path.read_bytes(), allow_values=allow_values)
        if result.status == "clean":
            failures.append(path)
    return failures


def _negative_failures(fixtures_root: Path, allow_values: set[str]) -> list[Path]:
    failures: list[Path] = []
    for path in sorted((fixtures_root / "negatives").glob("*")):
        if not path.is_file():
            continue
        result = redact(path.read_bytes(), allow_values=allow_values)
        if result.status != "clean":
            failures.append(path)
    return failures


def _omni_leaks(
    root: Path,
    allow_values: set[str],
    planted_literals: tuple[bytes, ...],
) -> list[Path]:
    omni_dir = root / ".omni"
    if not omni_dir.exists():
        return []

    leaks: list[Path] = []
    for path in sorted(omni_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.relative_to(omni_dir) == Path("audit") / "secrets.passed":
            continue
        if _path_has_leak(path, allow_values, planted_literals):
            leaks.append(path)
    return leaks


def _path_has_leak(
    path: Path,
    allow_values: set[str],
    planted_literals: tuple[bytes, ...],
) -> bool:
    if _path_contains_literal(path, planted_literals):
        return True
    if is_skiplisted_path(path):
        return True
    if path.stat().st_size <= _STREAM_SCAN_CHUNK_BYTES:
        return redact_path(path, allow_values=allow_values).status != "clean"
    return _path_has_stream_redaction(path, allow_values)


def _path_contains_literal(path: Path, literals: tuple[bytes, ...]) -> bool:
    if not literals:
        return False
    overlap = max(len(literal) for literal in literals) - 1
    tail = b""
    with path.open("rb") as handle:
        while chunk := handle.read(_STREAM_SCAN_CHUNK_BYTES):
            window = tail + chunk
            if any(literal in window for literal in literals):
                return True
            tail = window[-overlap:] if overlap > 0 else b""
    return False


def _path_has_stream_redaction(path: Path, allow_values: set[str]) -> bool:
    tail = b""
    with path.open("rb") as handle:
        while chunk := handle.read(_STREAM_SCAN_CHUNK_BYTES):
            window = tail + chunk
            result = redact(window, allow_values=allow_values)
            if result.status != "clean":
                return True
            tail = window[-_STREAM_SCAN_OVERLAP_BYTES:]
    return False


def _positive_fixture_literals(fixtures_root: Path, allow_values: set[str]) -> tuple[bytes, ...]:
    allowed = {value.encode("utf-8") for value in allow_values}
    literals: set[bytes] = set()
    for path in sorted((fixtures_root / "positives").glob("*")):
        if not path.is_file():
            continue
        payload = path.read_bytes().strip()
        if payload:
            literals.add(payload)
        for line in path.read_bytes().splitlines():
            literals.update(_literals_from_positive_line(line))
    return tuple(sorted((literal for literal in literals if literal not in allowed), key=len, reverse=True))


def _literals_from_positive_line(line: bytes) -> set[bytes]:
    stripped = line.strip()
    literals = {stripped} if stripped else set()
    for marker in (b"=", b"--token ", b"Bearer "):
        if marker in stripped:
            candidate = stripped.split(marker, 1)[1].strip()
            if candidate:
                literals.add(candidate)
    return literals


def _load_allow_values(root: Path) -> set[str]:
    path = root / ".omni" / "redaction-allow.txt"
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
