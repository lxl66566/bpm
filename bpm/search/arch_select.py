import functools
import logging as log
import platform
import unittest
from enum import Enum
from typing import Optional


class Combination(Enum):
    """
    Enum for the different ways of combining the select_list and prompt.
    """

    ALL = 0
    ANY = 1

    def fun(self):
        """
        Returns `all` or `any`
        """
        if self == Combination.ALL:
            return all
        elif self == Combination.ANY:
            return any
        else:
            raise ValueError("Unknown combination type")


class MatchPos(Enum):
    """
    Enum for the str matching position
    """

    ALL = 0
    BEGIN = 1
    END = 2

    def fun(self):
        """
        Returns a function `lambda x, y` indicates if x matches y. x is pattern, and y is str
        """
        if self == MatchPos.ALL:
            return lambda x, y: x in y  # noqa: E731
        elif self == MatchPos.BEGIN:
            return lambda x, y: y.startswith(x)  # noqa: E731
        elif self == MatchPos.END:
            return lambda x, y: y.endswith(x)  # noqa: E731
        else:
            raise ValueError("Unknown MatchPos")


def multi_in(parts: list, total: str):
    """
    return any strings in the list is a part of one string.
    """
    if isinstance(parts, str):
        parts = [parts]
    return any(x in total for x in parts)


def in_pair(pair: list, word: str) -> Optional[list]:
    """
    Returns pair if word is in pair, otherwise returns None.

    >>> in_pair(["12", "13"], "14")
    >>> in_pair(["12", "13"], "13")
    ['12', '13']
    """
    if word in pair:
        return pair
    return None


def select_list(
    select_list: list[str],
    prompts: list[str],
    combination: Combination = Combination.ALL,
    case_sensitive=False,
) -> list[str]:
    """
    Selects items from the given list and return.
    if no item were found, return the origin list, so the return list will not be empty.

    :param combination: ALL => every prompt should in the word, ANY => one or more prompt in the word.

    >>> select_list(["12", "13", "23"], ["1"])
    ['12', '13']
    >>> select_list(["12", "13", "23", "34"], ["1", "2"], Combination.ANY)
    ['12', '13', '23']
    >>> select_list(["12", "13", "23", "34", "21"], ["1", "2"], Combination.ALL)
    ['12', '21']
    """

    def is_valid(s: str):
        return combination.fun()(
            map(
                (lambda x: x in s)
                if case_sensitive
                else lambda x: x.lower() in s.lower(),
                prompts,
            )
        )

    return list(filter(is_valid, select_list)) or select_list


def sort_list(
    sort_list: list[str],
    prompts: list[str],
    combination=Combination.ANY,
    match_pos=MatchPos.ALL,
    case_sensitive=False,
    reverse=True,
) -> list[str]:
    """
    Sort items from the given list and return.

    :param combination: ALL => every prompt should in the word, ANY => one or more prompt in the word.
    :param reverse: If set True, the match options will be put in the start, otherwise put it in the end.

    >>> sort_list(["12", "13", "23"], ["2"])
    ['12', '23', '13']
    >>> sort_list(["12", "13", "23"], ["2"], match_pos=MatchPos.BEGIN)
    ['23', '12', '13']
    >>> sort_list(["12", "13", "23"], ["3"], match_pos=MatchPos.END)
    ['13', '23', '12']
    >>> sort_list(["12", "13", "23"], ["2"], combination=Combination.ANY)
    ['12', '23', '13']
    """

    def is_valid(s: str):
        return combination.fun()(
            map(
                lambda x: match_pos.fun()(x, s)
                if case_sensitive
                else match_pos.fun()(x.lower(), s.lower()),
                prompts,
            )
        )

    return sorted(sort_list, key=is_valid, reverse=reverse)


@functools.lru_cache()
def platform_map() -> list:
    plt = platform.system().lower()
    return (
        in_pair(["darwin", "macos"], plt)
        or in_pair(["windows", "win32", ".exe"], plt)
        or [plt]
    )


@functools.lru_cache()
def architecture_map():
    arch = platform.machine().lower()
    return (
        in_pair(["x86_64", "amd64", "x64"], arch)
        or in_pair(["aarch64", "armv8"], arch)
        or [arch]
    )


def select(assets: list):
    """
    select the best match item from assets.
    NOTE that this function will change the content of assets. (mut)
    """
    # 1. platform
    log.debug(f"platform filter: {platform_map()}")
    assets = select_list(assets, platform_map(), Combination.ANY)
    log.debug(f"platform selected assets: {assets}")

    # 2. architecture
    log.debug(f"architecture filter: {architecture_map()}")
    assets = select_list(assets, architecture_map(), Combination.ANY)

    # 3. put 7z in the end because linux users may not install p7zip
    assets = sort_list(assets, [".7z"], match_pos=MatchPos.END, reverse=False)

    if not assets:
        if __name__ == "__main__":
            raise ValueError("No valid asset found")
        else:
            from ..utils.exceptions import InvalidAssetError

            raise InvalidAssetError
    return assets


# region Test


class TestSortList(unittest.TestCase):
    def test_multi_in(self):
        self.assertTrue(multi_in(["a", "b"], "a"))
        self.assertTrue(multi_in(["win", "windo"], "windals"))
        self.assertTrue(multi_in("123", "1234"))
        self.assertFalse(multi_in(["13", "14"], "1234"))

    def test_select(self):
        assets = [
            "asd-macos-x86_64-123.zip",
            "asd-windows-x86_64-123.zip",
            "asd-linux-x86_64-123.zip",
            "asd-macos-aarch64-123.zip",
            "asd-windows-aarch64-123.zip",
            "asd-linux-aarch64-123.zip",
        ]
        assets = select(assets)
        self.assertTrue(multi_in(architecture_map(), assets[0]))
        self.assertTrue(multi_in(platform_map(), assets[0]))

    def test_select_typstyle(self):
        assets = [
            "typstyle-alpine-x64",
            "typstyle-alpine-x64.debug",
            "typstyle-darwin-arm64",
            "typstyle-darwin-arm64.dwarf",
            "typstyle-darwin-x64",
            "typstyle-darwin-x64.dwarf",
            "typstyle-linux-arm64",
            "typstyle-linux-arm64.debug",
            "typstyle-linux-armhf",
            "typstyle-linux-armhf.debug",
            "typstyle-linux-x64",
            "typstyle-linux-x64.debug",
            "typstyle-win32-arm64.exe",
            "typstyle-win32-arm64.pdb",
            "typstyle-win32-x64.exe",
            "typstyle-win32-x64.pdb",
        ]
        assets = select(assets)
        if platform.system() == "Windows" and platform.machine() == "AMD64":
            self.assertEqual(assets[0], "typstyle-win32-x64.exe")

    def test_sort_fastfetch(self):
        assets = [
            "fastfetch-linux-amd64.deb",
            "fastfetch-linux-amd64.rpm",
            "fastfetch-linux-amd64.tar.gz",
            "fastfetch-linux-amd64.zip",
        ]
        assets = sort_list(
            assets,
            [".tar", ".tar.gz", ".tar.xz", ".tar.bz2", ".zip", ".7z"],
            match_pos=MatchPos.END,
        )
        self.assertEqual(assets[0], "fastfetch-linux-amd64.tar.gz")


if __name__ == "__main__":
    import doctest

    doctest.testmod()
    unittest.main()
