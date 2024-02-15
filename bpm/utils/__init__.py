import functools
import logging as log
import os
import platform
import sys
import tempfile
import traceback
from pathlib import Path

TEST = False


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
        TEST = True
        result = func(*args, **kwargs)
        TEST = False
        return result

    return warpper
