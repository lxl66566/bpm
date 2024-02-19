# modify from https://pypi.org/project/windows-path-adder/
import logging as log
import platform
import re
import subprocess
from datetime import datetime
from pathlib import Path
from subprocess import CompletedProcess
from typing import List

_WINDOWS_PATH_PATTERN = re.compile(r"    PATH    (?P<type>.+)    (?P<value>.+)*")


class TryDecodeError(Exception):
    def __init__(self, byte_string: bytes, encodings: List[str]):
        super().__init__(
            f"[{byte_string}] decoding failed. tried encodings: [{encodings}]"
        )
        self.byte_string = byte_string
        self.encodings = encodings


class NotSupportError(Exception):
    def __init__(self, platform: str):
        super().__init__(f"current platform is not supported. [{platform}]")
        self.platform = platform


def _print(message):
    pass


def _command(*args, **kwargs) -> CompletedProcess:
    _print(f'command: [{" ".join(list(*args))}]')
    return subprocess.run(*args, **kwargs)


def _try_decode(
    byte_string: bytes, encodings: List[str] = ["utf-8", "cp949", "ansi"]
) -> str:
    for encoding in encodings:
        try:
            return byte_string.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise TryDecodeError(byte_string, encodings)


def add_windows_path(new_path: str) -> bool:
    """
    `Returns`: indicate whether the path add successfully
    """
    current_platform = platform.system()
    if current_platform != "Windows":
        raise NotSupportError(current_platform)

    current_type = "REG_SZ"
    current_path = None

    completed_process = _command(
        ["reg", "query", "HKCU\\Environment", "/v", "PATH"], capture_output=True
    )
    if completed_process.returncode == 0:
        stdout = _try_decode(completed_process.stdout)
        _print(stdout)
        match = _WINDOWS_PATH_PATTERN.search(stdout)
        if match:
            current_type = match.group("type")
            current_path = match.group("value")
            if current_path:
                current_path = current_path.strip().replace("\r", "").replace("\n", "")
                _print(f"current PATH: [{current_path}]")
            else:
                _print("environment variable PATH is empty.")

    elif completed_process.returncode == 1:
        _print("environment variable PATH does not exist.")
        _print(_try_decode(completed_process.stderr))

    else:
        completed_process.check_returncode()

    resolved_new_path = str(Path(new_path).resolve().absolute())
    _print(f"resolve new path. [{resolved_new_path}]")

    if current_path:
        if resolved_new_path in current_path.split(";"):
            _print(f"[{resolved_new_path}] exists in [{current_path}].")
            _print("do not add to PATH.")
            log.debug(f"[{resolved_new_path}] exists in PATH.")
            return False

    if current_path:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_key = f"PATH_{timestamp}"
        _print(f"backup PATH. [{current_path}] to [{backup_key}]")
        _command(
            [
                "reg",
                "add",
                "HKCU\\Environment",
                "/t",
                current_type,
                "/v",
                backup_key,
                "/d",
                current_path,
                "/f",
            ]
        ).check_returncode()

    path = f"{resolved_new_path};{current_path}" if current_path else resolved_new_path
    _command(
        [
            "reg",
            "add",
            "HKCU\\Environment",
            "/t",
            current_type,
            "/v",
            "PATH",
            "/d",
            path,
            "/f",
        ]
    ).check_returncode()
    log.warning(
        f"`{resolved_new_path}` added to PATH. Please click `OK` to confirm and apply it."
    )
    if _command(["rundll32", "sysdm.cpl,EditEnvironmentVariables"]).returncode != 0:
        log.warning(
            "Failed to open Environment Variable panel. You may need to relogin Windows to apply the PATH change."
        )
    return True
