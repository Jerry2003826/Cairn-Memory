"""Command parsing and safety checks for verify preflight."""

from __future__ import annotations

import shlex
from pathlib import Path

from omni.verify.deps import os, shutil

REASON_CODE_PARSE_ERROR_EMPTY_COMMAND = "parse_error_empty_command"
REASON_CODE_PARSE_ERROR_SHELL_OPERATOR = "parse_error_shell_operator"
REASON_CODE_PARSE_ERROR_SHELL_WRAPPER = "parse_error_shell_wrapper"
REASON_CODE_PARSE_ERROR_BATCH_METACHARACTER = "parse_error_batch_metacharacter"
REASON_CODE_PARSE_ERROR_INVALID_COMMAND = "parse_error_invalid_command"

WINDOWS_BATCH_EXTENSIONS = (".bat", ".cmd")
WINDOWS_BATCH_META_CHARS = ("&", "<", ">", "^", "%", "!")
ENV_WRAPPER_EXECUTABLES = {"env", "env.exe"}
POSIX_SHELL_WRAPPER_EXECUTABLES = {
    "bash",
    "bash.exe",
    "dash",
    "dash.exe",
    "ksh",
    "ksh.exe",
    "sh",
    "sh.exe",
    "zsh",
    "zsh.exe",
}
CMD_WRAPPER_EXECUTABLES = {"cmd", "cmd.exe"}
POWERSHELL_WRAPPER_EXECUTABLES = {
    "powershell",
    "powershell.exe",
    "pwsh",
    "pwsh.exe",
}
SHELL_WRAPPER_EXECUTABLES = (
    POSIX_SHELL_WRAPPER_EXECUTABLES
    | CMD_WRAPPER_EXECUTABLES
    | POWERSHELL_WRAPPER_EXECUTABLES
)
POWERSHELL_COMMAND_FLAGS = {
    "-c",
    "-command",
    "-commandwithargs",
    "-cwa",
    "-e",
    "-ec",
    "-encodedcommand",
    "-enc",
}
POSIX_SHELL_CLUSTER_FLAGS = set("abefhilmnptuvxc")
ENV_OPTIONS_WITH_VALUE = {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}


class VerifyCommandError(ValueError):
    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(message)


def _command_args(command: str, root_path: Path) -> list[str]:
    _reject_embedded_null(command)
    try:
        args = _split_command(command)
    except VerifyCommandError as exc:
        raise VerifyCommandError(
            exc.reason_code,
            f"could not parse verification command: {exc}",
        ) from exc
    if not args:
        raise VerifyCommandError(
            REASON_CODE_PARSE_ERROR_EMPTY_COMMAND,
            "could not parse verification command: empty command",
        )
    for arg in args:
        _reject_embedded_null(arg)
    try:
        resolved = _resolve_executable(args[0], root_path)
    except (OSError, ValueError) as exc:
        raise VerifyCommandError(
            REASON_CODE_PARSE_ERROR_INVALID_COMMAND,
            f"could not parse verification command: invalid executable path: {exc}",
        ) from exc
    _reject_embedded_null(resolved)
    if _is_windows_batch_file(resolved) and _has_windows_batch_meta(command):
        raise VerifyCommandError(
            REASON_CODE_PARSE_ERROR_BATCH_METACHARACTER,
            "could not parse verification command: Windows batch metacharacters "
            "are not supported",
        )
    args[0] = resolved
    return args


def _reject_embedded_null(value: str) -> None:
    if "\x00" in value:
        raise VerifyCommandError(
            REASON_CODE_PARSE_ERROR_INVALID_COMMAND,
            "could not parse verification command: embedded null byte",
        )


def _split_command(command: str) -> list[str]:
    if _has_unquoted_shell_operator(command):
        raise VerifyCommandError(
            REASON_CODE_PARSE_ERROR_SHELL_OPERATOR,
            "shell operators are not supported",
        )
    try:
        args = shlex.split(command, posix=True, comments=False)
    except ValueError as exc:
        raise VerifyCommandError(REASON_CODE_PARSE_ERROR_INVALID_COMMAND, str(exc)) from exc
    if _uses_shell_command_wrapper(args):
        raise VerifyCommandError(
            REASON_CODE_PARSE_ERROR_SHELL_WRAPPER,
            "shell interpreter wrappers are not supported",
        )
    return args


def _has_unquoted_shell_operator(command: str) -> bool:
    quote: str | None = None
    escaped = False
    index = 0
    while index < len(command):
        char = command[index]
        if escaped:
            escaped = False
            index += 1
            continue
        if char == "\\" and quote != "'":
            escaped = True
            index += 1
            continue
        if quote:
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
        elif char in {";", "|", "`"}:
            # Backtick triggers command substitution and must be rejected
            # alongside the classic separators.
            return True
        elif char == "&":
            # Both '&&' (logical and) and a lone '&' (background) are shell
            # control operators that the verify runner must not execute.
            return True
        index += 1
    return False


def _uses_shell_command_wrapper(args: list[str]) -> bool:
    if not args:
        return False
    executable = _executable_name(args[0])
    if executable in ENV_WRAPPER_EXECUTABLES:
        return _uses_shell_command_wrapper(_env_delegated_args(args[1:]))
    if executable not in SHELL_WRAPPER_EXECUTABLES:
        return False
    return any(_is_shell_command_flag(executable, arg) for arg in args[1:])


def _env_delegated_args(args: list[str]) -> list[str]:
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            return args[index + 1 :]
        if arg == "-":
            index += 1
            continue
        if _is_env_split_string_option(arg):
            return ["sh", "-c"]
        if _is_env_assignment(arg):
            index += 1
            continue
        if _is_env_option_with_joined_value(arg):
            index += 1
            continue
        if arg in ENV_OPTIONS_WITH_VALUE:
            index += 2
            continue
        if arg.startswith("-"):
            index += 1
            continue
        return args[index:]
    return []


def _is_env_split_string_option(value: str) -> bool:
    return (
        value in {"-S", "--split-string"}
        or value.startswith("--split-string=")
        or (value.startswith("-S") and value != "-S")
    )


def _is_env_assignment(value: str) -> bool:
    name, separator, _ = value.partition("=")
    return bool(separator and name) and not name.startswith("-")


def _is_env_option_with_joined_value(value: str) -> bool:
    if any(value.startswith(option + "=") for option in ENV_OPTIONS_WITH_VALUE):
        return True
    return any(
        value.startswith(option) and value != option
        for option in ("-u", "-C", "-S")
    )


def _executable_name(value: str) -> str:
    return value.replace("\\", "/").rsplit("/", 1)[-1].lower()


def _is_shell_command_flag(executable: str, value: str) -> bool:
    normalized = value.lower()
    if executable in CMD_WRAPPER_EXECUTABLES:
        return normalized == "/c"
    if executable in POWERSHELL_WRAPPER_EXECUTABLES:
        return normalized in POWERSHELL_COMMAND_FLAGS
    if executable not in POSIX_SHELL_WRAPPER_EXECUTABLES:
        return False
    if normalized == "-c":
        return True
    if not normalized.startswith("-") or normalized.startswith("--"):
        return False
    flags = normalized[1:]
    # POSIX shells accept clustered short flags such as -cl and -lc.
    return "c" in flags and set(flags) <= POSIX_SHELL_CLUSTER_FLAGS


def _resolve_executable(executable: str, root_path: Path) -> str:
    if _has_path_separator(executable):
        executable_path = Path(executable)
        if not executable_path.is_absolute():
            executable_path = root_path / executable_path
        return shutil.which(str(executable_path)) or str(executable_path)
    return shutil.which(executable, path=_path_for_cwd(root_path)) or executable


def _path_for_cwd(root_path: Path) -> str:
    entries: list[str] = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            entries.append(str(root_path))
            continue
        path = Path(entry)
        entries.append(str(path if path.is_absolute() else root_path / path))
    return os.pathsep.join(entries)


def _has_path_separator(value: str) -> bool:
    return "/" in value or "\\" in value


def _is_windows_batch_file(value: str) -> bool:
    return value.lower().endswith(WINDOWS_BATCH_EXTENSIONS)


def _has_windows_batch_meta(command: str) -> bool:
    return any(char in command for char in WINDOWS_BATCH_META_CHARS)
