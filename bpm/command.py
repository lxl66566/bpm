import logging as log
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from .install import auto_install, download_and_extract, restore
from .search import RepoHadler
from .storage import repo_group
from .utils import check_root, trace
from .utils.exceptions import RepoNotFoundError


def cli_install(args):
    check_root()
    for package in args.packages:
        if repo_group.find_repo(package)[1]:
            log.info(f"{package} is already installed.")
            continue
        repo = (
            RepoHadler(
                package,
                prefer_gnu=args.prefer_gnu,
                no_pre=args.no_pre,
                bin_name=args.bin_name or package,
                one_bin=args.one_bin,
            )
            .ask(quiet=args.quiet)
            .get_asset()
        )
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            main_path = download_and_extract(repo.asset, tmp_dir)
            try:
                auto_install(repo, main_path, rename=True)
                repo_group.insert_repo(repo)
                log.info(f"Successfully installed `{repo.name}`.")
            except Exception as e:
                log.error(f"Failed to install `{repo.name}`: {e}.")
                trace()
                log.error("Restoring...")
                # rollback.
                if repo.installed_files:
                    restore(repo.file_list)
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
            restore(repo.file_list)
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

    def update(repo: RepoHadler):
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
