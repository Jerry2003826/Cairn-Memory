from __future__ import annotations

from pathlib import Path

from omni import redact


def test_skiplisted_sensitive_paths_are_withheld(tmp_path: Path) -> None:
    names = [
        ".env",
        ".env.local",
        "prod.pem",
        "deploy.key",
        "cert.p12",
        "cert.pfx",
        "id_rsa",
        "id_ed25519.pub",
        "vault.kdbx",
        "app-credentials.json",
        ".netrc",
        ".npmrc",
        "terraform.tfstate",
        "secrets.local",
    ]

    for name in names:
        path = tmp_path / name
        path.write_text("raw secret that must not be returned", encoding="utf-8")
        result = redact.redact_path(path)
        assert result.status == "withheld", name
        assert result.detectors == ("skiplist",)
        assert b"raw secret" not in result.data


def test_non_skiplisted_path_uses_normal_redaction(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("api_key=normal-secret-value-123456", encoding="utf-8")

    result = redact.redact_path(path)

    assert result.status == "redacted"
    assert "secret_assignment" in result.detectors
    assert b"normal-secret-value-123456" not in result.data
