import functools
import tempfile
from pathlib import Path


class RepoNotFoundError(FileNotFoundError):
    def __init__(self, repo=""):
        super().__init__(f"Repository '{repo}' not found")


class TarPathTraversalException(Exception):
    def __init__(self, message: str = "Tar Path exceed boundary."):
        super().__init__(message)


# unused code
def with_temp(func):
    @functools.wraps(func)
    def warpper():
        with tempfile.TemporaryDirectory() as tmpdir:
            return func(Path(tmpdir))

    return warpper
