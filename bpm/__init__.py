import argparse
import logging

from storage import info_repos

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)

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
    "-q",
    "--quiet",
    action="store_true",
    help="not ask, install the best match repo",
)
install_parser.add_argument(
    "--one-bin",
    metavar="BIN_NAME",
    nargs="?",
    help="install given binary only. Use package name as binary name by default.",
)
install_parser.add_argument(
    "--no-pre",
    action="store_true",
    help="do not include pre-release",
)
install_parser.add_argument(
    "--prefer-gnu",
    action="store_true",
    help="bpm prefers musl target by default, you can change this default option.",
)

remove_parser = subparsers.add_parser("remove", aliases=["r"])
remove_parser.add_argument("packages", nargs="+", help="Package name to remove")

# not support search, temporarily
# search_parser = subparsers.add_parser("search", aliases=["s"])
# search_parser.add_argument("packages", nargs="+", help="Package name to search")

update_parser = subparsers.add_parser("update", aliases=["u"])
update_parser.add_argument("packages", nargs="+", help="Package name to update")

info_parser = subparsers.add_parser("info", help="Info package.")
info_parser.add_argument(
    "package", nargs="?", help="Package name to info. If not given, show all packages."
)
info_parser.set_defaults(func=lambda _: info_repos())
# info_parser.set_defaults(func=lambda x: print(x))


args = parser.parse_args()
args.func(args)
