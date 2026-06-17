"""Minimal JSONC-to-JSON conversion for project-local config files."""

from __future__ import annotations


def jsonc_to_json(current: str) -> str:
    return _strip_jsonc_trailing_commas(_strip_jsonc_comments(current))


def _strip_jsonc_comments(current: str) -> str:
    cleaned: list[str] = []
    index = 0

    while index < len(current):
        char = current[index]

        if char == '"':
            string_literal, index = _json_string_literal(current, index)
            cleaned.append(string_literal)
            continue

        next_char = current[index + 1 : index + 2]
        if char == "/" and next_char == "/":
            index += 2
            while index < len(current) and current[index] not in "\r\n":
                index += 1
            continue
        if char == "/" and next_char == "*":
            index += 2
            closed = False
            while index < len(current) - 1:
                if current[index] == "\n":
                    cleaned.append("\n")
                if current[index] == "*" and current[index + 1] == "/":
                    index += 2
                    closed = True
                    break
                index += 1
            if not closed:
                raise ValueError("unterminated block comment")
            continue

        cleaned.append(char)
        index += 1

    return "".join(cleaned)


def _strip_jsonc_trailing_commas(current: str) -> str:
    cleaned: list[str] = []
    index = 0

    while index < len(current):
        char = current[index]

        if char == '"':
            string_literal, index = _json_string_literal(current, index)
            cleaned.append(string_literal)
            continue

        if char == ",":
            next_index = _next_non_whitespace(current, index + 1)
            if current[next_index : next_index + 1] in "]}":
                index += 1
                continue

        cleaned.append(char)
        index += 1

    return "".join(cleaned)


def _json_string_literal(current: str, start: int) -> tuple[str, int]:
    index = start + 1
    escaped = False

    while index < len(current):
        char = current[index]
        index += 1

        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            break

    return current[start:index], index


def _next_non_whitespace(current: str, start: int) -> int:
    index = start
    while index < len(current) and current[index].isspace():
        index += 1
    return index
