import functools
import logging as log
import os
import posixpath
import sys
import tempfile
import traceback
from pathlib import Path, WindowsPath
from typing import Union

from ..lib.windowspathadder import add_windows_path
from .constants import BIN_PATH, LINUX, WINDOWS

TEST = False


def set_dry_run():
    global TEST
    TEST = True


def is_root() -> bool:
    """
    only linux needs root.
    """
    if LINUX and os.geteuid() != 0:
        return False
    return True


def check_root():
    if not is_root():
        sys.exit("You need to have root privileges to run this command.")


def error_exit(msg: str):
    """
    Exit with error message.
    """
    log.error(msg)
    sys.exit(1)


def trace():
    """
    Trace back only in debug mode.
    """
    if log.getLogger().isEnabledFor(log.DEBUG):
        traceback.print_exc()


def ensure_windows_path():
    """
    ensure that the bpm's `BIN_PATH` is in windows $PATH environment.
    """
    assert WINDOWS, "This function only works on Windows."
    if not TEST:
        add_windows_path(BIN_PATH)


def windows_path_to_windows_bash(p: Union[WindowsPath, str]) -> str:
    """
    convert a windows path to posix path string. example:

    >>> windows_path_to_windows_bash("C:\\Users\\lxl\\bpm\\bin")
    "/c/Users/lxl/bpm/bin"
    """
    p = WindowsPath(p)
    return posixpath.join(
        "/", p.drive.rstrip(":").lower(), p.relative_to(p.anchor).as_posix()
    )


def windows_path_to_wsl(p: Union[WindowsPath, str]) -> str:
    """
    convert a windows path to wsl path string. example:

    >>> windows_path_to_wsl("C:\\Users\\lxl\\bpm\\bin")
    "/mnt/c/Users/lxl/bpm/bin"
    """

    return posixpath.join("/mnt", windows_path_to_windows_bash(p).lstrip("/"))


# unused code
def with_temp(func):
    @functools.wraps(func)
    def warpper():
        with tempfile.TemporaryDirectory() as tmpdir:
            return func(Path(tmpdir))

    return warpper


def with_test(func):
    """
    enable TEST global var only in this function.
    """

    @functools.wraps(func)
    def warpper(*args, **kwargs):
        global TEST
        record = TEST
        TEST = True
        result = func(*args, **kwargs)
        TEST = record
        return result

    return warpper


import unittest  # noqa: E402


class Test(unittest.TestCase):
    def test_windows_path_convert(self):
        if not WINDOWS:
            return
        self.assertEqual(
            windows_path_to_windows_bash(r"C:\Users\lxl\bpm\bin"),
            "/c/Users/lxl/bpm/bin",
        )
        self.assertEqual(
            windows_path_to_wsl(r"C:\Users\lxl\bpm\bin"),
            "/mnt/c/Users/lxl/bpm/bin",
        )


if __name__ == "__main__":
    unittest.main()
