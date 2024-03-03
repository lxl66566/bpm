import argparse
import sys

from .command import cli_alias, cli_info, cli_install, cli_remove, cli_update


def value_in(value, in_list):
    if value not in in_list:
        raise argparse.ArgumentTypeError(f"`{value}` is not in {in_list}")
    return value


parser = argparse.ArgumentParser(
    prog="bpm",
    description="Bin package manager. See https://github.com/lxl66566/bpm for more information.",
)
subparsers = parser.add_subparsers(
    title="subcommands",
    dest="command",
    help="You can use 'bpm <subcommand> -h' to get more infomation.",
)

install_parser = subparsers.add_parser(
    "install", aliases=["i"], help="Install packages."
)
install_parser.add_argument("packages", nargs="+", help="Package name to install")
install_parser.add_argument(
    "-b",
    "--bin-name",
    nargs="?",
    help="specify the binary executable filename, otherwise use package name by default.",
)
install_parser.add_argument(
    "-l",
    "--local",
    nargs="?",
    metavar="Archive",
    help="install from local archive.",
)
install_parser.add_argument(
    "-q",
    "--quiet",
    action="store_true",
    help="not ask, install the best match repo.",
)
install_parser.add_argument(
    "--one-bin",
    action="store_true",
    help="install given binary only. Use package name as binary name by default.",
)
# github api not support info pre releases. https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28#get-the-latest-release
# install_parser.add_argument(
#     "--no-pre",
#     action="store_true",
#     help="do not include pre-releases.",
# )
install_parser.add_argument(
    "--prefer-gnu",
    action="store_true",
    help="bpm prefers musl target by default, you can change this default option.",
)
install_parser.add_argument(
    "-n",
    "--dry-run",
    action="store_true",
    help="print the install position, but not install actually.",
)
install_parser.add_argument(
    "-i",
    "--interactive",
    action="store_true",
    help="select asset interactively.",
)
install_parser.add_argument(
    "--sort",
    nargs="?",
    type=lambda value: value_in(
        value, ["stars", "forks", "help-wanted-issues", "updated"]
    ),
    help="sort param in github api, use `best-match` by default. The value could be `stars`, `forks`, `help-wanted-issues`, `updated`.",
)
install_parser.set_defaults(func=cli_install)


remove_parser = subparsers.add_parser("remove", aliases=["r"], help="Remove packages.")
remove_parser.add_argument("packages", nargs="+", help="Package names to remove.")
remove_parser.add_argument(
    "--soft",
    action="store_true",
    help="only remove item in database, do not delete softwares themselves.",
)
remove_parser.set_defaults(func=cli_remove)

# not support search, temporarily
# search_parser = subparsers.add_parser("search", aliases=["s"])
# search_parser.add_argument("packages", nargs="+", help="Package name to search")

update_parser = subparsers.add_parser("update", aliases=["u"], help="Update packages.")
update_parser.add_argument(
    "packages", nargs="*", help="Package names to update. Update all by default."
)
update_parser.set_defaults(func=cli_update)

info_parser = subparsers.add_parser("info", help="Info package.")
info_parser.add_argument(
    "package", nargs="?", help="Package name to info. If not given, show all packages."
)
info_parser.set_defaults(func=cli_info)

alias_parser = subparsers.add_parser(
    "alias", help="Alias package. (Windows only; Linux use shell alias instead.)"
)
alias_parser.add_argument("new_name", help="New name of the bin.")
alias_parser.add_argument("old_name", help="Old name of the bin.")
alias_parser.set_defaults(func=cli_alias)


def main():
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        exit(1)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
