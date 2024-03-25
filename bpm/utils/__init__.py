import functools
import logging as log
import os
import posixpath
import sys
import tempfile
import traceback
from pathlib import Path, WindowsPath

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


def assert_exit(condition: bool, msg: str):
    """
    Exit with error message if condition is not met.
    """
    if not condition:
        error_exit(msg)


def trace():
    """
    Trace back only in debug mode.
    """
    if log.getLogger().isEnabledFor(log.DEBUG):
        traceback.print_exc()


def multi_in(parts: list | str, total: str):
    """
    return any strings in the list is a part of one string.
    """
    if isinstance(parts, str):
        parts = [parts]
    return any(x in total for x in parts)


def ensure_windows_path():
    assert WINDOWS, "This function only works on Windows."
    if not TEST:
        add_windows_path(BIN_PATH)


def select_interactive(options: list[str]) -> str:
    """
    select an option from a list.
    """
    for i, option in enumerate(options):
        print(f"{i+1}. {option}")
    while True:
        try:
            choice = int(input("Enter your choice: "))
            if 1 <= choice <= len(options):
                return options[choice - 1]
            else:
                raise ValueError
        except ValueError:
            print(
                f"Invalid choice. Please enter a number between 1 and {len(options)}."
            )
        except KeyboardInterrupt:
            print("Interrupted by user.")
            exit(0)


def windows_path_to_windows_bash(p: WindowsPath | str) -> str:
    """
    convert a windows path to posix path string. example:

    >>> windows_path_to_windows_bash("C:\\Users\\lxl\\bpm\\bin")
    "/c/Users/lxl/bpm/bin"
    """
    p = WindowsPath(p)
    return posixpath.join(
        "/", p.drive.rstrip(":").lower(), p.relative_to(p.anchor).as_posix()
    )


def windows_path_to_wsl(p: WindowsPath | str) -> str:
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
    def test_multi_in(self):
        self.assertTrue(multi_in(["a", "b"], "a"))
        self.assertTrue(multi_in(["win", "windo"], "windals"))
        self.assertTrue(multi_in("123", "1234"))
        self.assertFalse(multi_in(["13", "14"], "1234"))

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
