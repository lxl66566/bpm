import logging as log
from copy import copy
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

from .install import auto_install, download_and_extract, extract, remove
from .search import RepoHandler
from .storage import repo_group
from .utils import check_root, error_exit, set_dry_run, trace
from .utils.constants import BIN_PATH, WINDOWS
from .utils.exceptions import RepoNotFoundError


def parse_name_or_url(name_or_url: str) -> tuple[str, bool]:
    """
    Parse the name or url of a package.
    `Returns`: a tuple with two elements: first is the true name, second is the flag of whether it is a url.
    """
    test_parse = urlparse(name_or_url)
    if test_parse.netloc == "github.com":
        return RepoHandler.get_info_by_url(name_or_url)[1], True
    return name_or_url, False


def download_and_install(args, repo: RepoHandler, rename=True):
    try:
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            if args.local:
                with Path(args.local).open("rb") as f:
                    main_path = extract(f, tmp_dir)
            else:
                main_path = download_and_extract(repo.asset, tmp_dir)
            auto_install(repo, main_path, rename=rename)
    except Exception as e:
        raise e


def cli_install(args):
    if args.interactive and args.quiet:
        log.error("Cannot use both --interactive and --quiet.")
        exit(1)
    if args.quiet:
        log.getLogger().setLevel(log.WARNING)
    if args.dry_run:
        set_dry_run()
    else:
        check_root()
    if args.local and len(args.packages) > 1:
        log.error(
            "Cannot install multiple packages from local. Please install them separately."
        )
        exit(1)
    for package in args.packages:
        real_name, is_url = parse_name_or_url(package)
        if not args.dry_run and repo_group.find_repo(real_name)[1]:
            log.info(f"{real_name} is already installed.")
            continue

        # search
        try:
            if is_url:
                repo = (
                    RepoHandler(
                        real_name,
                        prefer_gnu=args.prefer_gnu,
                        one_bin=args.one_bin,
                        asset_filter=args.filter,
                    )
                    .set_by_url(package)
                    .with_bin_name(args.bin_name)
                )
            else:
                repo = RepoHandler(
                    package,
                    prefer_gnu=args.prefer_gnu,
                    one_bin=args.one_bin,
                    asset_filter=args.filter,
                ).with_bin_name(args.bin_name)
                if not args.local:
                    repo.ask(quiet=args.quiet, sort=args.sort)
            if not args.local:
                repo.get_asset(interactive=args.interactive)
        except Exception as e:
            log.error(f"Failed on searching `{package}`: {e}")
            trace()
            exit(1)

        # install
        try:
            download_and_install(args, repo)
            print(f"Successfully installed `{repo.name}`.")
            if WINDOWS:
                bins = copy(repo.file_list)
                bins = filter(lambda x: x.endswith(".lnk"), bins)
                bins = map(lambda x: Path(x).stem, bins)
                bins = map(lambda x: f"`{x}`", bins)
                print(
                    f"You can press `Win+r`, enter {', '.join(bins)} to start software, or execute in cmd."
                )
            if not args.dry_run:
                repo_group.insert_repo(repo)
        except Exception as e:
            log.error(f"Failed to install `{repo.name}`: {e}")
            trace()
            log.error("Restoring...")
            # rollback.
            remove(repo.file_list)
            error_exit("Files restored. Exiting...")


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
            log.info(
                f"""Removing `{package}`{" in soft mode" if args.soft else ""}..."""
            )
            args.soft or remove(repo.file_list)
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
        log.info(f"Failed list: {failed}")


def cli_update(args):
    check_root()
    failed = []

    def update(repo: RepoHandler):
        try:
            log.info(f"Updating `{repo.name}`...")
            result = repo.update_asset()
            if result:
                log.info(
                    f"`{repo.name}` has an update: {result[0]} -> {result[1]}. Updating..."
                )
                download_and_install(args, repo, rename=False)
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
                repo_group.save()
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
    assert (
        args.old_name != args.new_name
    ), "Alias name cannot be the same as the original."

    file = list(BIN_PATH.glob(args.old_name + "*"))
    if not file:
        log.error(f"Script `{args.old_name}` not found.")
        exit(1)
    if len(file) > 1:
        name = file[0].with_suffix("")
        assert name == file[1].with_suffix(
            ""
        ), "Both lnk should point to the same file."

    repo_group.alias_lnk(args.old_name, args.new_name)
    log.info(f"Alias `{args.old_name}` to `{args.new_name}`.")
