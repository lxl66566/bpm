import argparse
import sys

from .command import cli_info, cli_install, cli_remove, cli_update

parser = argparse.ArgumentParser(
    prog="bpm",
    description="Bin package manager. See https://github.com/lxl66566/bpm for more information.",
)
subparsers = parser.add_subparsers(
    title="subcommands", dest="command", help="action to take"
)

install_parser = subparsers.add_parser("install", aliases=["i"])
install_parser.add_argument("packages", nargs="+", help="Package name to install")
install_parser.add_argument(
    "-b",
    "--bin-name",
    nargs="?",
    help="specify the binary executable filename, otherwise use package name by default.",
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
install_parser.add_argument(
    "--no-pre",
    action="store_true",
    help="do not include pre-releases.",
)
install_parser.add_argument(
    "--prefer-gnu",
    action="store_true",
    help="bpm prefers musl target by default, you can change this default option.",
)
install_parser.set_defaults(func=cli_install)


remove_parser = subparsers.add_parser("remove", aliases=["r"])
remove_parser.add_argument("packages", nargs="+", help="Package names to remove.")
remove_parser.set_defaults(func=cli_remove)

# not support search, temporarily
# search_parser = subparsers.add_parser("search", aliases=["s"])
# search_parser.add_argument("packages", nargs="+", help="Package name to search")

update_parser = subparsers.add_parser("update", aliases=["u"])
update_parser.add_argument(
    "packages", nargs="*", help="Package names to update. Update all by default."
)
update_parser.set_defaults(func=cli_update)

info_parser = subparsers.add_parser("info", help="Info package.")
info_parser.add_argument(
    "package", nargs="?", help="Package name to info. If not given, show all packages."
)
info_parser.set_defaults(func=cli_info)


def main():
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        exit(1)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
