from __future__ import annotations

import json

import pytest

from omni.jsonc import jsonc_to_json


def test_jsonc_to_json_removes_comments_and_trailing_commas() -> None:
    parsed = json.loads(
        jsonc_to_json(
            """
{
  // line comment
  "url": "https://example.com/path//kept",
  "text": "literal /* kept */",
  "items": [
    "README.md",
  ],
  /* block comment */
}
""".lstrip()
        )
    )

    assert parsed == {
        "items": ["README.md"],
        "text": "literal /* kept */",
        "url": "https://example.com/path//kept",
    }


def test_jsonc_to_json_rejects_unclosed_block_comment() -> None:
    with pytest.raises(ValueError, match="unterminated block comment"):
        jsonc_to_json('{"instructions": []} /* unfinished')
