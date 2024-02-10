import logging as log
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional


def rename_old(_path: Path):
    _path.rename(_path.with_name(_path.name + ".old"))


def install_with_rename(_from: Path, _to: Path, mode: Optional[int] = None):
    _to.parent.mkdir(parents=True, exist_ok=True)
    if _to.exists():
        rename_old(_to)
    _from.replace(_to)
    log.info(f"{_from} -> {_to}")
    if mode:
        _to.chmod(mode)


def merge_dir(_from: Path | str, _to: Path | str):
    """
    merge two dirs, the overlap file will be renamed to `*.old`, the previous `*.old` file will be replace.
    """
    _from = Path(_from)
    _to = Path(_to)
    _to.mkdir(parents=True, exist_ok=True)
    for src_file in _from.rglob("*"):
        if src_file.is_dir():
            continue
        dest_file = _to / src_file.relative_to(_from)
        install_with_rename(src_file, dest_file)


import unittest  # noqa: E402


class Test(unittest.IsolatedAsyncioTestCase):
    async def test_merge_dir(self):
        with TemporaryDirectory() as tmp_path:
            tmp_path = Path(tmp_path)
            test1 = tmp_path / "test1"
            test2 = tmp_path / "test2"
            test1.mkdir()
            test2.mkdir()
            file = test1 / "file"
            file.write_text("Hello")
            subfile = test1 / "folder/subfile"
            subfile.parent.mkdir(parents=True)
            subfile.write_text("World")
            overwrite1 = test1 / "overwrite"
            overwrite2 = test2 / "overwrite"
            overwrite1.write_text("123")
            overwrite2.write_text("456")

            merge_dir(test1, test2)

            self.assertEqual((test2 / "file").read_text(), "Hello")
            self.assertEqual((test2 / "folder/subfile").read_text(), "World")
            self.assertEqual((test2 / "overwrite").read_text(), "123")
            self.assertEqual((test2 / "overwrite.old").read_text(), "456")


if __name__ == "__main__":
    unittest.main()
