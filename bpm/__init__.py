import argparse
import logging

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

remove_parser = subparsers.add_parser("remove", aliases=["r"])
remove_parser.add_argument("packages", nargs="+", help="Package name to remove")

search_parser = subparsers.add_parser("search", aliases=["r"])
search_parser.add_argument("packages", nargs="+", help="Package name to search")

update_parser = subparsers.add_parser("update", aliases=["u"])
update_parser.add_argument("packages", nargs="+", help="Package name to update")

info_parser = subparsers.add_parser("info", help="Info package.")
info_parser.add_argument(
    "package", nargs="?", help="Package name to info. If not given, show all packages."
)


args = parser.parse_args()
