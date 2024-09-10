from pretty_assert import assert_eq

from bpm.utils import windows_path_to_windows_bash, windows_path_to_wsl
from bpm.utils.constants import WINDOWS


class TestUtils:
    def test_windows_path_convert(self):
        if not WINDOWS:
            return
        assert_eq(
            windows_path_to_windows_bash(r"C:\Users\lxl\bpm\bin"),
            "/c/Users/lxl/bpm/bin",
        )
        assert_eq(
            windows_path_to_wsl(r"C:\Users\lxl\bpm\bin"),
            "/mnt/c/Users/lxl/bpm/bin",
        )
