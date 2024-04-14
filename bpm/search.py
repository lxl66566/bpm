# ruff: noqa: E731

import functools
import logging as log
import platform
import posixpath
import sys
from enum import Enum
from functools import reduce
from pprint import pprint
from typing import Optional, Union
from urllib.parse import urljoin, urlparse

import requests

from .utils import multi_in, select_interactive
from .utils.constants import INFO_BASE_STRING, OPTION_REPO_NUM, WINDOWS
from .utils.exceptions import AssetNotFoundError, InvalidAssetError, RepoNotFoundError


class Combination(Enum):
    """
    Enum for the different ways of combining the select_list and prompt.
    """

    ALL = 0
    ANY = 1


class MatchPos(Enum):
    """
    Enum for the str matching position
    """

    ALL = 0
    BEGIN = 1
    END = 2


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
    comb_func = any if combination == Combination.ANY else all
    is_valid = lambda s: comb_func(
        map(
            (lambda x: x in s)
            if case_sensitive
            else (lambda x: x.lower() in s.lower()),
            prompts,
        )
    )
    return list(filter(is_valid, select_list)) or select_list


def sort_list(
    sort_list: list[str],
    prompts: list[str],
    combination=Combination.ALL,
    match_pos=MatchPos.ALL,
    case_sensitive=False,
) -> list[str]:
    """
    Sort items from the given list and return.

    :param combination: ALL => every prompt should in the word, ANY => one or more prompt in the word.


    >>> sort_list(["12", "13", "23"], ["2"])
    ['12', '23', '13']
    """
    comb_func = any if combination == Combination.ANY else all
    if match_pos == MatchPos.ALL:
        match_func = lambda a, b: a not in b
    elif match_pos == MatchPos.BEGIN:
        match_func = lambda a, b: not b.beginswith(a)
    elif match_pos == MatchPos.END:
        match_func = lambda a, b: not b.endswith(a)

    is_valid = lambda s: comb_func(
        map(
            (lambda x: match_func(x, s))
            if case_sensitive
            else (lambda x: match_func(x.lower(), s.lower())),
            prompts,
        )
    )
    return sorted(sort_list, key=is_valid)


@functools.lru_cache()
def platform_map() -> list:
    return [platform.system()]


@functools.lru_cache()
def architecture_map():
    pair1 = ["x86_64", "amd64"]
    if platform.machine() in pair1:
        return pair1
    else:
        return [platform.machine()]


class RepoHandler:
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.bin_name = name
        self.site = "github"
        self.repo_name = None
        self.repo_owner = None
        self.asset = None
        self.asset_filter = []
        self.version = None
        self.installed_files: list[str] = []
        self.prefer_gnu: bool = False
        self.no_pre: bool = False
        self.one_bin: bool = False

        self.set(**kwargs)
        if WINDOWS:
            assert name not in ("app", "bin"), "Invalid repo name."

    def __str__(self) -> str:
        return INFO_BASE_STRING.format(
            self.name or "", self.url or "", self.version or ""
        )

    def __lt__(self, other: "RepoHandler"):
        return self.name < other.name

    def __eq__(self, __value: object) -> bool:
        return self.name == __value.name

    def __getstate__(self):
        state = self.__dict__.copy()
        return state

    def __setstate__(self, state):
        """
        Add backward Compatibility
        """
        self.__dict__.update(state)
        if "asset_filter" not in state:
            self.asset_filter = []

    def set(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    def with_bin_name(self, bin_name: Union[str, None]):
        if WINDOWS:
            self.bin_name = bin_name.rstrip(".exe") + ".exe" if bin_name else "*.exe"
        else:
            self.bin_name = bin_name or self.name
        return self

    @property
    def url(self) -> Optional[str]:
        if not self.repo_name or not self.repo_owner:
            return None
        return urljoin(
            f"https://{self.site}.com/", posixpath.join(self.repo_owner, self.repo_name)
        )

    @property
    def api_base(self):
        if self.site == "github":
            return "https://api.github.com"
        else:
            raise NotImplementedError

    @property
    def file_list(self) -> list[str]:
        """
        Get the "IndexSet" of `installed_files`.
        """
        # same as `unique` function, keep them
        self.installed_files = reduce(
            lambda re, x: re + [x] if x not in re else re, self.installed_files, []
        )
        return self.installed_files

    def add_file_list(self, file):
        self.installed_files.append(str(file))

    @staticmethod
    def get_info_by_fullname(fullname: str) -> tuple[str, str]:
        """
        Returns: a tuple of (repo_owner, repo_name)
        """
        # why does https://t.me/withabsolutex/1479 happens?
        r = fullname.strip("/").split("/")
        assert len(r) == 2, "parsing invalid fullname"
        return tuple(r)

    @staticmethod
    def get_info_by_url(url: str):
        """
        set repo_owner and repo_name from url
        """
        return RepoHandler.get_info_by_fullname(urlparse(url).path)

    def set_by_url(self, url: str):
        """
        set repo_owner and repo_name from url
        """
        info = self.get_info_by_url(url)
        self.repo_owner = info[0]
        self.repo_name = info[1]
        return self

    def search(self, page=1, sort=None) -> Optional[list[str]]:
        """
        get the 5 top repos to download

        `sort`: sort the search result. Use best-match by default.
            More info: https://docs.github.com/rest/search/search?apiVersion=2022-11-28#search-repositories
        """
        params = {
            "q": f"{self.name} in:name",
            "page": page,
            "per_page": OPTION_REPO_NUM,
        }
        if sort:
            params["sort"] = sort
        r = requests.get(
            urljoin(self.api_base, posixpath.join("search", "repositories")),
            params=params,
        )

        if r.status_code == 200:
            data = r.json()
            if data["items"]:
                return [x["html_url"] for x in data["items"]]
            else:
                raise RepoNotFoundError
        else:
            r.raise_for_status()

    def ask(self, quiet: bool = False, sort=None):
        """
        ask what repo to install.
        please call `search()` before ask.
        """
        page = 1
        while True:
            repo_selections = self.search(page, sort)
            if not repo_selections:
                raise RepoNotFoundError
            if quiet:
                log.info(f"auto select repo: {repo_selections[0]}")
                return self.set_by_url(repo_selections[0])
            for i, item in enumerate(repo_selections):
                print(f"{i+1}: {item}")
            try:
                temp = input(
                    "please select a repo to download (default 1), `m` for more, `p` for previous: "
                ).strip()
                if not temp:
                    temp = "1"
                elif temp == "m":
                    page += 1
                    continue
                elif temp == "p":
                    page -= 1
                    continue
                return self.set_by_url(repo_selections[int(temp) - 1])
            except KeyboardInterrupt:
                print("Canceled.")
                exit(0)
            except IndexError:
                print(
                    f"Invalid input: the number should not be more than {OPTION_REPO_NUM}",
                    file=sys.stderr,
                )
                exit(1)
            except ValueError:
                print("Invalid input: please input a valid number.", file=sys.stderr)
                exit(1)

    def get_asset(self, interactive: bool = False):
        """
        get version and filter out which asset link to download
        """
        assert self.url is not None, "use ask() before get_asset"
        api = urljoin(
            self.api_base,
            posixpath.join("repos", self.repo_owner, self.repo_name, "releases"),
        )

        r: list = requests.get(api).json()
        log.debug(f"asset api: {api}")
        if not isinstance(r, list):
            log.error(f"repo {self.repo_owner}/{self.repo_name} not found.")
            raise RepoNotFoundError

        r = list(filter(lambda x: bool(x["assets"]), r))
        if len(r) == 0:
            raise AssetNotFoundError

        self.version = r[0]["tag_name"]
        assets: list[str] = [x["browser_download_url"] for x in r[0]["assets"]]

        if interactive:
            self.asset = select_interactive(assets)
            log.info(f"selected asset: {self.asset}")
            return self

        # asset filter
        if self.asset_filter:
            assets = list(filter(lambda a: multi_in(self.asset_filter, a), assets))

        # select
        # 1. platform
        log.debug(f"platform filter: {platform_map()}")
        assets = select_list(assets, platform_map(), Combination.ANY)
        log.debug(f"platform selected assets: {assets}")

        # 2. architecture
        log.debug(f"architecture filter: {architecture_map()}")
        assets = select_list(assets, architecture_map(), Combination.ANY)

        # 3. musl or gnu
        if not self.prefer_gnu:
            assets = sort_list(assets, ["musl"])

        # 4. tar, zip, 7z, other
        assets = sort_list(assets, [".7z"], match_pos=MatchPos.END)
        if WINDOWS:
            assets = sort_list(assets, [".tar."])
            assets = sort_list(assets, [".zip"], match_pos=MatchPos.END)
        else:
            assets = sort_list(assets, [".zip"], match_pos=MatchPos.END)
            assets = sort_list(assets, [".tar."])

        if not assets:
            raise InvalidAssetError
        self.asset = assets[0]
        log.info(f"selected asset: {self.asset}")
        return self

    def update_asset(self) -> Optional[Union[tuple[str, str], tuple[None, None]]]:
        """
        update assets list. If a repo was installed locally, it will always return (None, None).

        `Returns`: `None` if has no update, `(old_version, new_version)` if has update.
        """
        old_version = self.version
        if not old_version:
            return None, None
        self.get_asset()
        if old_version == self.version:
            return None
        return (old_version, self.version)


import unittest  # noqa: E402


class Test(unittest.TestCase):
    def test_search(self):
        test = RepoHandler("eza").ask(quiet=True).get_asset()
        self.assertEqual(
            test.url,
            "https://github.com/eza-community/eza",
        )
        pprint(vars(test))

    def test_sort(self):
        temp = [RepoHandler("eza"), RepoHandler("abcd"), RepoHandler("xy")]
        temp.sort()
        self.assertEqual(temp[0].name, "abcd")
        self.assertEqual(temp[1].name, "eza")
        self.assertEqual(temp[2].name, "xy")

    def test_get_filelist(self):
        test = RepoHandler("eza").set(installed_files=["a", "b", "a", "c"])
        self.assertListEqual(test.file_list, ["a", "b", "c"])

    def test_parse_url(self):
        test = RepoHandler("yazi").set_by_url("https://github.com/sxyazi/yazi")
        self.assertEqual(test.repo_owner, "sxyazi")
        self.assertEqual(test.repo_name, "yazi")


if __name__ == "__main__":
    import doctest

    unittest.main()
    doctest.testmod()
