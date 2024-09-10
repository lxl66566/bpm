import io
import logging as log
from pathlib import Path
from tempfile import TemporaryDirectory

from pretty_assert import assert_, assert_eq

import bpm.utils as utils
from bpm.install import (
    download_and_extract,
    extract,
    install,
    install_on_linux,
    merge_dir,
    rename_old,
    rename_old_rev,
    restore,
)

log.basicConfig(level=log.DEBUG)


class TestInstall:
    def test_rename_old_and_rev(self):
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            test = tmp_dir / "test1"
            test.touch()
            rename_old(test)
            assert_(test.with_suffix(".old").exists())
            assert_(not test.exists())
            rename_old_rev(test)
            assert_(test.exists())

    def test_merge_dir(self):
        def make_test_dirs(tmp_dir):
            tmp_dir = Path(tmp_dir)
            test1 = tmp_dir / "test1"
            test2 = tmp_dir / "test2"
            test1.mkdir()
            test2.mkdir()
            file = test1 / "file"
            file.write_text("Hello")
            subfile = test1 / "folder" / "subfile"
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

            assert_eq((test2 / "file").read_text(), "Hello")
            assert_eq((test2 / "folder/subfile").read_text(), "World")
            assert_eq((test2 / "overwrite").read_text(), "123")
            assert_eq((test2 / "overwrite.old").read_text(), "456")

            print("recorder:", myrecorder)
            restore(myrecorder)
            assert_eq((test2 / "overwrite").read_text(), "456")

        with TemporaryDirectory() as tmp_dir:
            test1, test2 = make_test_dirs(tmp_dir)
            merge_dir(test1, test2, rename=False)
            assert_(not (test2 / "overwrite.old").exists())

    def test_extract(self):
        assets_path = Path(".") / "test_assets"
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            with (assets_path / "noroot.tar.gz").open("rb") as f:
                main = extract(io.BytesIO(f.read()), tmp_dir, "noroot.tar.gz")
                assert_eq(main, tmp_dir)
                assert_((main / "1").exists())
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            with (assets_path / "root.tar.gz").open("rb") as f:
                main = extract(io.BytesIO(f.read()), tmp_dir, "root.tar.gz")
                assert_eq(main, tmp_dir / "root")
                assert_((main / "1").exists())
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            with (assets_path / "noroot.zip").open("rb") as f:
                main = extract(io.BytesIO(f.read()), tmp_dir, "noroot.zip")
                assert_eq(main, tmp_dir)
                assert_((main / "1").exists())

    @utils.with_test
    def test_dry_run(self):
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            src = tmp_dir / "src"
            dst = tmp_dir / "dst"
            src.touch()
            install(src, dst)
            assert_(not dst.exists())

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
            install_on_linux(main, "eza", pkgdst=dst)
            assert_((bin / "eza").exists())

            main = download_and_extract(
                "https://github.com/BurntSushi/ripgrep/releases/download/14.1.0/ripgrep-14.1.0-x86_64-unknown-linux-musl.tar.gz",
                src,
            )
            install_on_linux(main, "rg", pkgdst=dst)
            for i in usr.rglob("*"):
                log.debug(i) if i.is_file() else None
            assert_((bin / "rg").exists())
            assert_((fish_completion / "rg.fish").exists())
