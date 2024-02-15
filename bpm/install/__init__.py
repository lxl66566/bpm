import io
import logging as log
import platform
import tarfile
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import requests
import tqdm

from ..search import RepoHadler
from ..utils.exceptions import TarPathTraversalException


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
    """
    install a file to system.
    """
    _to = Path(_to)
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
    Install one dir and all files to another.

    `rename`: Whether the overlap files to be renamed to `*.old`. If rename, the previous `*.old` file will be replaced.
    """
    _from = Path(_from)
    _to = Path(_to)
    _to.mkdir(parents=True, exist_ok=True)

    for src_file in _from.rglob("*"):
        install(
            src_file,
            _to / src_file.relative_to(_from),
            rename=rename,
            recorder=recorder,
        )


def restore(recorder: Optional[list[str]] = None):
    """
    uninstall: remove installed files and restore *.old files.
    """
    if not recorder:
        return
    for file in map(lambda x: Path(x), reversed(recorder)):
        if file.is_dir():
            file.rmdir()
        else:
            file.unlink(missing_ok=True)
        log.info(f"deleting {file}")
        rename_old_rev(file)


def check_if_tar_safe(tar_file: tarfile.TarFile) -> bool:
    """CVE-2007-4559"""
    all_members = tar_file.getnames()
    root_dir = Path(all_members[0]).parent.resolve()
    for member in all_members:
        if not Path(member).resolve().is_relative_to(root_dir):
            return False
    return True


def extract(buffer: io.BytesIO, to_dir: Path) -> Path:
    """
    extract tar | zip | 7z to dir.

    `Returns`: the "main" path of extracted files.
    """
    try:
        with tarfile.open(fileobj=buffer, mode="r") as file:
            if not check_if_tar_safe(file):
                raise TarPathTraversalException
            file.extractall(path=to_dir)
    except tarfile.ReadError:
        try:
            with zipfile.ZipFile(buffer, "r") as file:
                file.extractall(path=to_dir)
        except zipfile.BadZipFile:
            import py7zr

            with py7zr.SevenZipFile(buffer, "r") as file:
                file.extractall(path=to_dir)

    temp = list(to_dir.glob("*"))
    if len(temp) == 1 and temp[0].is_dir():
        return temp[0]
    return to_dir


def download_and_extract(url: str, to_dir: Path) -> Path:
    """
    Download an archive from url and extract to dir.

    `Returns`: the "main" path of extracted files.
    """
    try:
        with requests.get(url, stream=True, timeout=5) as response:
            response.raise_for_status()
            # Download the file in chunks and save it to a memory buffer
            # content-length may be empty, default to 0
            file_size = int(response.headers.get("Content-Length", 0))
            bar_size = 1024
            # fetch 8 KB at a time
            chunk_size = 8192
            # how many bars are there in a chunk?
            chunk_bar_size = chunk_size / bar_size
            # bars are by KB
            num_bars = int(file_size / bar_size)

            buffer = io.BytesIO()
            # noinspection PyTypeChecker
            with tqdm.tqdm(
                disable=None,  # disable on non-TTY
                total=num_bars,
                unit="KB",
                desc=url.split("/")[-1],
            ) as pbar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        buffer.write(chunk)
                        pbar.update(chunk_bar_size)

            # Process the file in memory (e.g., extract its contents)
            buffer.seek(0)
            # Process the buffer (e.g., extract its contents)
            return extract(buffer=buffer, to_dir=to_dir)
    except KeyboardInterrupt:
        pbar.close()
        log.warning("Keyboard Cancelled")
        exit(1)


def install_on_linux(
    path: Path,
    # how about using multiple candidate bin_names : list[str] ?
    bin_name: str,
    one_bin: bool = False,
    rename: bool = True,
    recorder: Optional[list[str]] = None,
    pkgdst=Path("/usr"),
):
    """
    Install files to a linux system.
    1. Single binary
    2. System structure-like
    3. completions

    `path`: The "main path" dir of files to be installed.
    """
    pkgdst = Path(pkgdst)

    def install_to(_from: Path, _to: Path, mode: Optional[int] = None):
        install(_from, _to / _from.name, rename=rename, mode=mode, recorder=recorder)

    def install_bin(p: Path):
        """Install binary file."""
        if hasattr(install_bin, "called"):
            log.debug(f"already installed {p.name}")
            return
        install_to(p, pkgdst / "bin", mode=0o755)
        install_bin.called = True

    def install_completions(path: Path):
        """Install completions from a dir."""
        log.debug(f"installing completions from {path}")
        if not path.is_dir():
            log.warning(f"trying to install {path} as completions: not a directory")
            return
        for file in path.rglob("*.fish"):
            # $fish_complete_path
            install_to(
                file,
                pkgdst / "share/fish/vendor_completions.d",
            )
        for file in path.rglob("*.bash"):
            install_to(
                file,
                pkgdst / "share/bash-completion/completions",
            )
        for file in path.rglob("_*"):
            if "zsh" in file.read_text():
                install_to(
                    file,
                    pkgdst / "share/zsh/site-functions",
                )

    first_layer: list[Path] = list(path.glob("*"))
    assert first_layer, f"{path} is empty"

    # 1. only install one bin
    if one_bin or len(first_layer) == 1:
        bin = next(path.glob("*" if len(first_layer) == 1 else bin_name))
        first_layer.remove(bin)
        install_bin(bin)
        if one_bin:
            return

    for file in first_layer:
        # 2. merge all files to coordinate position
        match file.name:
            case "lib":
                merge_dir(file, pkgdst / "lib", rename=rename, recorder=recorder)
            case "include":
                merge_dir(file, pkgdst / "include", rename=rename, recorder=recorder)
            case "share":
                merge_dir(file, pkgdst / "share", rename=rename, recorder=recorder)
            case "bin":
                merge_dir(file, pkgdst / "bin", rename=rename, recorder=recorder)
            case "man":
                merge_dir(file, pkgdst / "share/man", rename=rename, recorder=recorder)
            # 3. deal with other circumstance.
            case name:
                if name.startswith("complet"):
                    install_completions(file)
                elif name == bin_name and file.is_file():
                    install_bin(file)
                else:
                    log.debug(f"cannot match {name}.")

    if not any(map(lambda x: x.startswith("/usr/bin"), recorder)):
        log.warning("No binary file found, please check the release package.")


def auto_install(
    repo: RepoHadler,
    pkgsrc: Path,
    rename: bool = True,
):
    """
    Install by different platforms.
    """

    match platform.system():
        case "Linux":
            install_on_linux(
                pkgsrc, repo.bin_name, repo.one_bin, rename, repo.installed_files
            )
        case _:
            raise NotImplementedError(f"{platform.system()} is not supported now.")


import unittest  # noqa: E402


class Test(unittest.TestCase):
    def test_rename_old_and_rev(self):
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            test = tmp_dir / "test1"
            test.touch()
            rename_old(test)
            self.assertTrue(test.with_suffix(".old").exists())
            self.assertFalse(test.exists())
            rename_old_rev(test)
            self.assertTrue(test.exists())

    def test_merge_dir(self):
        def make_test_dirs(tmp_dir):
            tmp_dir = Path(tmp_dir)
            test1 = tmp_dir / "test1"
            test2 = tmp_dir / "test2"
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

        with TemporaryDirectory() as tmp_dir:
            test1, test2 = make_test_dirs(tmp_dir)
            myrecorder = []
            merge_dir(test1, test2, recorder=myrecorder)

            self.assertEqual((test2 / "file").read_text(), "Hello")
            self.assertEqual((test2 / "folder/subfile").read_text(), "World")
            self.assertEqual((test2 / "overwrite").read_text(), "123")
            self.assertEqual((test2 / "overwrite.old").read_text(), "456")

            print("recorder:", myrecorder)
            restore(myrecorder)
            self.assertEqual((test2 / "overwrite").read_text(), "456")

        with TemporaryDirectory() as tmp_dir:
            test1, test2 = make_test_dirs(tmp_dir)
            merge_dir(test1, test2, rename=False)
            self.assertFalse((test2 / "overwrite.old").exists())

    def test_extract(self):
        src_path = Path(__file__).parent.parent.parent.resolve() / "tests"
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            with (src_path / "noroot.tar.gz").open("rb") as f:
                main = extract(f, tmp_dir)
                self.assertEqual(main, tmp_dir)
                self.assertTrue((main / "1").exists())
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            with (src_path / "root.tar.gz").open("rb") as f:
                main = extract(f, tmp_dir)
                self.assertEqual(main, tmp_dir / "root")
                self.assertTrue((main / "1").exists())
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            with (src_path / "noroot.zip").open("rb") as f:
                main = extract(f, tmp_dir)
                self.assertEqual(main, tmp_dir)
                self.assertTrue((main / "1").exists())

    def simulate_install(self):
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            src = tmp_dir / "src"
            dst = tmp_dir / "dst"
            usr = dst / "usr"
            bin = usr / "bin"
            fish_completion = dst / "usr/share/fish/vendor_completions.d"
            bash_completion = dst / "usr/share/bash-completion/completions"
            zsh_completion = dst / "usr/share/zsh/site-functions"
            src.mkdir()
            bin.mkdir(parents=True, exist_ok=True)
            fish_completion.mkdir(parents=True, exist_ok=True)
            bash_completion.mkdir(parents=True, exist_ok=True)
            zsh_completion.mkdir(parents=True, exist_ok=True)
            main = download_and_extract(
                "https://github.com/eza-community/eza/releases/download/v0.17.2/eza_x86_64-unknown-linux-musl.tar.gz",
                src,
            )
            install_on_linux(main, "eza", pkgdst=usr)
            self.assertTrue((bin / "eza").exists())

            main = download_and_extract(
                "https://github.com/BurntSushi/ripgrep/releases/download/14.1.0/ripgrep-14.1.0-x86_64-unknown-linux-musl.tar.gz",
                src,
            )
            install_on_linux(main, "rg", pkgdst=usr)
            for i in usr.rglob("*"):
                log.debug(i) if i.is_file() else None
            self.assertTrue((bin / "rg").exists())
            self.assertTrue((fish_completion / "rg.fish").exists())


if __name__ == "__main__":
    log.basicConfig(level=log.DEBUG)
    unittest.main()
