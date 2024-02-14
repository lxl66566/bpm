import functools
import tempfile
from pathlib import Path

TEST = False


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
