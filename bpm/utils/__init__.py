import functools
import logging as log
import os
import platform
import sys
import tempfile
import traceback
from pathlib import Path

TEST = False


def set_dry_run():
    global TEST
    TEST = True


def is_root() -> bool:
    """
    only linux needs root.
    """
    if platform.system() == "Linux" and os.geteuid() != 0:
        return False
    return True


def check_root():
    if not is_root():
        sys.exit("You need to have root privileges to run this command.")


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


# unused code
def with_temp(func):
    @functools.wraps(func)
    def warpper():
        with tempfile.TemporaryDirectory() as tmpdir:
            return func(Path(tmpdir))

    return warpper


def with_test(func):
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


if __name__ == "__main__":
    unittest.main()
