import logging as log
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional


def rename_old(_path: Path):
    _path.rename(_path.with_name(_path.name + ".old"))


def rename_old_rev(_path: Path):
    old = _path.with_name(_path.name + ".old")
    if old.exists():
        old.rename(_path)
        log.info(f"restoring {old} -> {_path}")


def install(
    _from: Path,
    _to: Path,
    rename: bool = True,
    mode: Optional[int] = None,
    recorder: Optional[list[str]] = None,
):
    if _from.is_dir():
        _to.mkdir(exist_ok=True)
        log.info(f"mkdir {_from} -> {_to}")
        recorder is not None and recorder.append(str(_to.absolute()))
        return
    if _to.exists():
        if rename:
            rename_old(_to)
        else:
            _to.unlink()
    _from.replace(_to)
    log.info(f"{_from} -> {_to}")
    recorder is not None and recorder.append(str(_to.absolute()))
    mode and _to.chmod(mode)


def merge_dir(
    _from: Path | str,
    _to: Path | str,
    rename: bool = True,
    recorder: Optional[list[str]] = None,
):
    """
    merge two dirs, the overlap file will be renamed to `*.old`, the previous `*.old` file will be replace.
    """
    _from = Path(_from)
    _to = Path(_to)
    _to.mkdir(parents=True, exist_ok=True)
    for src_file in _from.rglob("*"):
        dest_file = _to / src_file.relative_to(_from)
        install(src_file, dest_file, rename=rename, recorder=recorder)


def restore(recorder: Optional[list[str]] = None):
    if not recorder:
        return
    for file in map(lambda x: Path(x), reversed(recorder)):
        if file.is_dir():
            file.rmdir()
        else:
            file.unlink(missing_ok=True)
        log.info(f"deleting {file}")
        rename_old_rev(file)


import unittest  # noqa: E402


class Test(unittest.TestCase):
    def test_rename_old_and_rev(self):
        with TemporaryDirectory() as tmp_path:
            tmp_path = Path(tmp_path)
            test = tmp_path / "test1"
            test.touch()
            rename_old(test)
            self.assertTrue(test.with_suffix(".old").exists())
            self.assertFalse(test.exists())
            rename_old_rev(test)
            self.assertTrue(test.exists())

    def test_merge_dir(self):
        log.basicConfig(level=log.DEBUG)

        def make_test_dirs(tmp_path):
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
            return test1, test2

        with TemporaryDirectory() as tmp_path:
            test1, test2 = make_test_dirs(tmp_path)
            myrecorder = []
            merge_dir(test1, test2, recorder=myrecorder)

            self.assertEqual((test2 / "file").read_text(), "Hello")
            self.assertEqual((test2 / "folder/subfile").read_text(), "World")
            self.assertEqual((test2 / "overwrite").read_text(), "123")
            self.assertEqual((test2 / "overwrite.old").read_text(), "456")

            print("recorder:", myrecorder)
            restore(myrecorder)
            self.assertEqual((test2 / "overwrite").read_text(), "456")

        with TemporaryDirectory() as tmp_path:
            test1, test2 = make_test_dirs(tmp_path)
            merge_dir(test1, test2, rename=False)
            self.assertFalse((test2 / "overwrite.old").exists())


if __name__ == "__main__":
    unittest.main()
