import io
import logging as log
import os
import platform
import shutil
import subprocess
import tarfile
import zipfile
from contextlib import suppress
from pathlib import Path
from typing import Optional, Union

import requests
import tqdm

import bpm.utils as utils

from ..search import RepoHandler
from ..utils.constants import APP_PATH, BIN_PATH, CONF_PATH, LINUX, WINDOWS
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

    def record():
        recorder is not None and recorder.append(str(_to.absolute()))

    if utils.TEST:
        log.info(f"dry run: {_to}")
        record()
        return
    _to = Path(_to)
    if _from.is_dir():
        _to.mkdir(exist_ok=True)
        log.info(f"mkdir {_from} -> {_to}")
        record()
        return
    if _to.exists():
        if rename:
            rename_old(_to)
        else:
            _to.unlink()

    shutil.copy2(_from, _to)
    log.info(f"{_from} -> {_to}")
    record()
    mode and _to.chmod(mode)


def merge_dir(
    _from: Union[Path, str],
    _to: Union[Path, str],
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


def remove_on_windows(recorder: Optional[list[str]] = None, partial: bool = False):
    """
    Remove a repo on windows.
    It will delete all given files and folders.

    :param partial: Only remove the install folder, not scripts.
    """
    assert WINDOWS, "This function only works on windows"

    if utils.TEST:
        for file in recorder or []:
            log.info(f"dry run: Remove {file}.")
        return

    new_recorder = []

    while recorder:
        file = Path(recorder.pop())
        # all bpm data should be stored inside CONF_PATH.
        assert file.is_relative_to(
            CONF_PATH
        ), f"UNSAFE REMOVE! trying to remove: {file}"

        if file.is_dir():
            shutil.rmtree(file)
            log.info(f"Remove dir {file}.")
        elif not partial:
            file.unlink()
            log.info(f"Remove {file}.")
        else:
            new_recorder.append(file)

    recorder = list(reversed(new_recorder))


def remove(recorder: Optional[list[str]] = None):
    """
    remove repo on any platform.
    """
    if WINDOWS:
        remove_on_windows(recorder)
    elif LINUX:
        restore(recorder)


def check_if_tar_safe(tar_file: tarfile.TarFile) -> bool:
    """CVE-2007-4559"""
    all_members = tar_file.getnames()
    root_dir = Path(all_members[0]).parent.resolve()
    for member in all_members:
        if not Path(member).resolve().is_relative_to(root_dir):
            return False
    return True


def extract(buffer: io.BytesIO, to_dir: Path, name: str = "") -> Path:
    """
    extract tar / zip / 7z to dir.

    `Returns`: the "main" path of extracted files.
    """

    log.debug(f"extracting `{name}` to `{to_dir}`")
    try:
        if name.endswith(".zip"):
            with zipfile.ZipFile(buffer, "r") as file:
                file.extractall(path=to_dir)
        elif name.endswith(".7z"):
            try:
                import py7zr

                py7zr.SevenZipFile(buffer, "r").extractall(path=to_dir)
            except ImportError:
                utils.error_exit("cannot extract this file without py7zr module.")
        else:
            if ".tar" not in name:
                log.warning(f"unknown file type: {name}")
            with tarfile.open(fileobj=buffer, mode="r") as file:
                if not check_if_tar_safe(file):
                    raise TarPathTraversalException
                file.extractall(path=to_dir)
    except Exception as e:
        utils.error_exit(f"cannot extract file: {e}")

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

            buffer.seek(0)
            filename = url.strip("/").rpartition("/")[-1]

            # do not extract .exe and .msi file on windows, give it to installer
            if WINDOWS and (os.path.splitext(url)[-1] in [".exe", ".msi"]):
                file = to_dir / filename
                file.write_bytes(buffer.getvalue())
                return to_dir
            return extract(buffer=buffer, to_dir=to_dir, name=filename)
    except KeyboardInterrupt:
        # suppressed not binding lint
        with suppress(NameError):
            pbar.close()  # type: ignore
        log.warning("Keyboard Cancelled")
        exit(1)


def install_on_linux(
    path: Path,
    # TODO: how about using multiple candidate bin_names : list[str] ?
    bin_name: str,
    one_bin: bool = False,
    rename: bool = True,
    recorder: Optional[list[str]] = None,
    pkgdst=Path("/"),
):
    """
    Install files to a linux system.
    1. Single binary
    2. System structure-like
    3. completions
    4. services

    `path`: The "main path" dir of files to be installed.
    """
    assert LINUX, "Not a linux system"
    pkgdst = Path(pkgdst)

    log.debug(f"install_on_linux() with params: {locals()}")

    def install_to(_from: Path, _to: Path, mode: Optional[int] = None):
        """
        install file to a folder.
        """
        install(
            _from,
            _to / _from.name,
            rename=rename,
            mode=mode,
            recorder=recorder,
        )

    def install_bin(p: Path):
        """Install binary file."""
        if hasattr(install_bin, "called"):
            log.debug(f"already installed {p.name}")
            return
        install_to(p, pkgdst / "usr/bin", mode=0o755)
        install_bin.called = True  # type: ignore

    def install_service(p: Path):
        """Install service file."""
        with suppress(FileNotFoundError):
            install_to(p, pkgdst / "usr/lib/systemd/system/", mode=0o644)

    def install_completions(path: Path):
        """Install completions from a dir."""
        log.debug(f"installing completions from {path}")
        if not path.is_dir():
            log.warning(f"trying to install {path} as completions: not a directory")
            return
        with suppress(FileNotFoundError):
            for file in path.rglob("*.fish"):
                # $fish_complete_path
                install_to(
                    file, pkgdst / "usr/share/fish/vendor_completions.d", mode=0o644
                )
        with suppress(FileNotFoundError):
            for file in path.rglob("*.bash"):
                install_to(
                    file, pkgdst / "usr/share/bash-completion/completions", mode=0o644
                )
        with suppress(FileNotFoundError):
            for file in path.rglob("_*"):
                if "zsh" in file.read_text():
                    install_to(
                        file, pkgdst / "usr/share/zsh/site-functions", mode=0o644
                    )

    first_layer: list[Path] = list(path.glob("*"))
    assert first_layer, f"{path} is empty"

    # 1. only install one bin
    if one_bin or len(first_layer) == 1:
        # if there is only one file (not dir), assert it's a binary file, whatever the name it is.
        if len(first_layer) == 1 and first_layer[0].is_file():
            bin = first_layer[0]
        else:
            bin = next(path.rglob(bin_name))
        if bin is not None and bin.is_file():
            log.debug(f"judge out bin: selected {bin}")
            install_bin(bin)
            bin.unlink()
            if one_bin:
                return

    for file in path.glob("*"):
        # 2. merge all files to coordinate position
        if file.name == "usr":
            merge_dir(file, pkgdst / "usr", rename=rename, recorder=recorder)
        elif file.name == "lib":
            merge_dir(file, pkgdst / "usr/lib", rename=rename, recorder=recorder)
        elif file.name == "include":
            merge_dir(file, pkgdst / "usr/include", rename=rename, recorder=recorder)
        elif file.name == "share":
            merge_dir(file, pkgdst / "usr/share", rename=rename, recorder=recorder)
        elif file.name == "bin":
            merge_dir(file, pkgdst / "usr/bin", rename=rename, recorder=recorder)
        elif file.name == "man":
            merge_dir(file, pkgdst / "usr/share/man", rename=rename, recorder=recorder)
        # 3. deal with other circumstance.
        else:
            name = file.name
            if name.startswith("complet"):
                install_completions(file)
            elif name == bin_name and file.is_file():
                install_bin(file)
            else:
                log.debug(f"cannot match {name}.")

    # 4 install service file
    for file in path.rglob("*.service"):
        install_service(file)

    # check binary
    if not any(map(lambda x: x.startswith("/usr/bin"), recorder or [])):
        log.warning("No binary file found, please check the release package.")


def install_on_windows(
    repo: RepoHandler,
    pkgsrc: Path,
):
    """
    Install files to a windows system.
    1. move all files to a folder.
    2. make lnk for GUI binary files.
    3. make a cmd for CLI binary files.
    4. make a bash script for using in windows bash.

    `path`: The "main path" dir of files to be installed.
    """
    assert WINDOWS, "This function only supports Windows."

    # pylink3 only available on windows
    from pylnk3 import for_file  # type: ignore

    pkgsrc = Path(pkgsrc)

    APP_PATH.mkdir(parents=True, exist_ok=True)
    BIN_PATH.mkdir(parents=True, exist_ok=True)
    REPO_PATH = APP_PATH / repo.name
    remove_on_windows(repo.file_list, True)

    # try to install msi package from pkgsrc, avoiding copying
    if install_msi(pkgsrc):
        return

    # 1. move all files to a folder.
    if utils.TEST:
        pkgdst = pkgsrc
        log.info(f"dry run: Install package to {REPO_PATH}.")
    else:
        pkgdst = Path(shutil.move(pkgsrc, REPO_PATH))
        log.info(f"Install package to {REPO_PATH}.")
        repo.add_file_list(REPO_PATH)

    bin_files = []
    for file in pkgdst.rglob(repo.bin_name):
        if not file.is_file():
            continue
        bin_files.append(file)
        link_name = file.with_suffix("").name
        # 234. lnk binary files.
        link_path = (BIN_PATH / link_name).with_suffix(".lnk")
        cmd_path = (BIN_PATH / link_name).with_suffix(".cmd")
        sh_path = (BIN_PATH / link_name).with_suffix("")
        if utils.TEST:
            log.info(f"dry run: Create lnk: {file} -> {link_path}")
            log.info(f"dry run: Create cmd: {file} -> {cmd_path}")
            log.info(f"dry run: Create sh: {file} -> {cmd_path}")
            continue
        link_path.exists() and link_path.unlink()
        cmd_path.exists() and cmd_path.unlink()
        sh_path.exists() and sh_path.unlink()

        for_file(str(file), str(link_path))
        repo.add_file_list(link_path)
        log.info(f"Create lnk: {file} -> {link_path}")

        cmd_path.write_text(f"""@echo off\n"{file.absolute()}" %*""")
        repo.add_file_list(cmd_path)
        log.info(f"Create cmd: {file} -> {cmd_path}")

        # needs LF for WSL
        sh_path.write_bytes(
            f"""#!/bin/sh
if [ "$(uname)" != "Linux" ]; then
    "{utils.windows_path_to_windows_bash(file)}" $@
else
    "{utils.windows_path_to_wsl(file)}" $@
fi
""".encode()
        )
        repo.add_file_list(sh_path)
        log.info(f"Create sh: {file} -> {sh_path}")

    if not bin_files:
        log.warning(f"No binary file found in {pkgdst}.")
    else:
        print(f"Successfully installed `{repo.name}`.")
        temp = ", ".join(map(lambda x: f"""`{x.with_suffix("").name}`""", bin_files))
        print(
            f"""You can press `Win+r`, enter {temp} to start software, or execute in cmd."""
        )

    # ensure windows bin path
    utils.ensure_windows_path()


def install_msi(pkgsrc: Path):
    """
    Install an MSI package on Windows.

    Args:
        pkgsrc (Path): The path to the directory containing the MSI package.

    Returns:
        bool: True if the MSI package is successfully found and opened, False otherwise.

    Raises:
        AssertionError: If the function is called on a non-Windows platform.
        AssertionError: If the pkgsrc is not a directory.

    The function searches for MSI files in the `pkgsrc` directory.
    If there is exactly one MSI file, it opens the MSI package.
    If no MSI files are found in the `pkgsrc` directory or multiple MSI files are found, it returns False.
    """

    assert WINDOWS, "This function only supports Windows."
    pkgsrc = Path(pkgsrc)
    assert pkgsrc.is_dir(), "pkgsrc must be a directory."
    if temp := list(pkgsrc.glob("*.msi")):
        if len(temp) != 1:
            log.debug(f"multiple msi files found: {temp}, do not install msi.")
            return False
        msi_file = temp[0]
        log.info(f"Start to install {msi_file}. Please install it manually.")
        subprocess.run(f"msiexec /i {msi_file}", shell=True)
        log.warn(
            "Note: this package will not be managed by bpm, but you can still update it from bpm."
        )
        return True
    return False


def auto_install(
    repo: RepoHandler,
    pkgsrc: Path,
    rename: bool = True,
):
    """
    Install by different platforms.
    """

    if platform.system() == "Linux":
        install_on_linux(
            pkgsrc, repo.bin_name, repo.one_bin, rename, repo.installed_files
        )
    elif platform.system() == "Windows":
        install_on_windows(repo, pkgsrc)
    else:
        raise NotImplementedError(f"{platform.system()} is not supported now.")
