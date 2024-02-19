import logging as log
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from simpleufcs import UFCS

from .install import auto_install, download_and_extract, remove
from .search import RepoHandler
from .storage import repo_group
from .utils import check_root, set_dry_run, trace
from .utils.constants import BIN_PATH, WINDOWS
from .utils.exceptions import RepoNotFoundError


def cli_install(args):
    if args.dry_run:
        set_dry_run()
    else:
        check_root()
    for package in args.packages:
        if not args.dry_run and repo_group.find_repo(package)[1]:
            log.info(f"{package} is already installed.")
            continue
        repo = (
            RepoHandler(
                package,
                prefer_gnu=args.prefer_gnu,
                one_bin=args.one_bin,
            )
            .with_bin_name(args.bin_name)
            .ask(quiet=args.quiet)
            .get_asset()
        )
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            main_path = download_and_extract(repo.asset, tmp_dir)
            try:
                auto_install(repo, main_path, rename=True)
                log.info(f"Successfully installed `{repo.name}`.")
                if WINDOWS:
                    bins = (
                        UFCS(repo.file_list)
                        .filter(lambda x: x.endswith(".lnk"))
                        .map(lambda x: Path(x).stem)
                        .map(lambda x: f"`{x}`")
                    )
                    log.info(
                        f"You can press `Win+r`, type {', '.join(bins)} and Enter to start software.\nIf you want to use it in cmd, add `.lnk` suffix for them."
                    )
                if not args.dry_run:
                    repo_group.insert_repo(repo)

            except Exception as e:
                log.error(f"Failed to install `{repo.name}`: {e}.")
                trace()
                log.error("Restoring...")
                # rollback.
                remove(repo.file_list)
                log.error("Files restored.")
                sys.exit("Exiting...")


def cli_remove(args):
    check_root()
    failed = []
    for package in args.packages:
        repo = repo_group.find_repo(package)[1]
        if not repo:
            log.info(f"Package `{package}` is not installed.")
            failed.append(package)
            continue
        try:
            log.info(f"Removing `{package}`...")
            remove(repo.file_list)
            repo_group.remove_repo(package)
        except Exception as e:
            failed.append(package)
            log.error(f"Failed to remove `{package}`: {e}")
            trace()
            continue
        log.info(f"`{package}` removed successfully.")
    log.info(
        f"Removing complete. Total: {len(args.packages)}, Success: {len(args.packages)-len(failed)}"
    )
    if failed:
        log.info(f"Failed: {failed}")


def cli_update(args):
    check_root()
    failed = []

    def update(repo: RepoHandler):
        try:
            log.info(f"Updating `{repo.name}`...")
            if result := repo.update_asset():
                log.info(
                    f"`{repo.name}` has an update: {result[0]} -> {result[1]}. Updating..."
                )
                with TemporaryDirectory() as tmp_dir:
                    tmp_dir = Path(tmp_dir)
                    main_path = download_and_extract(repo.asset, tmp_dir)
                    auto_install(repo, main_path, rename=False)
                log.info(f"`{repo.name}` updated successfully.")
            else:
                log.info(f"`{repo.name}` is the newest.")
        except Exception as e:
            failed.append(repo.name)
            log.error(f"Failed to update {repo.name}: {e}")
            trace()

    if not args.packages:  # update all
        num = len(repo_group.repos)
        for repo in repo_group.repos:
            update(repo)
    else:  # update some
        num = len(args.packages)
        for name in args.packages:
            _, repo = repo_group.find_repo(name)
            if repo:
                update(repo)
            else:
                failed.append(name)
                log.error(f"Package `{name}` not found.")

    log.info(f"Update complete. Total: {num}, Success: {num-len(failed)}")
    if failed:
        log.info(f"Failed: {failed}")


def cli_info(args):
    try:
        if not args.package:
            repo_group.info_repos()
        else:
            repo_group.info_one_repo(str(args.package))
    except RepoNotFoundError as e:
        log.error(e)
        exit(1)


def cli_alias(args):
    assert WINDOWS, "Alias command is only supported on Windows."

    def lnk_deal(n):
        return n.rstrip(".lnk") + ".lnk"

    args.old_name = lnk_deal(args.old_name)
    args.new_name = lnk_deal(args.new_name)
    file = list(BIN_PATH.glob(args.old_name))
    if not file:
        log.error(f"Lnk `{args.old_name}` not found.")
        exit(1)
    assert len(file) == 1, "Found multiple binaries with the same name."
    file = file[0]
    repo_group.alias_lnk(file, BIN_PATH / args.new_name)
    log.info(f"Alias `{args.old_name}` to `{args.new_name}`.")
