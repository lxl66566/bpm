import logging as log
import platform
from pprint import pprint
from typing import Optional

import requests

from .utils.constants import INFO_BASE_STRING, OPTION_REPO_NUM
from .utils.exceptions import RepoNotFoundError


class RepoHadler:
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.site = "github"
        self.repo_name = None
        self.repo_owner = None
        self.asset = None
        self.version = None
        self.installed_files: list[str] = []

        self.set(**kwargs)

    def __str__(self) -> str:
        return INFO_BASE_STRING.format(
            self.name or "", self.url or "", self.version or ""
        )

    def __lt__(self, other: "RepoHadler"):
        return self.name < other.name

    def set(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    @property
    def url(self) -> Optional[str]:
        if not self.repo_name or not self.repo_owner:
            log.warning("repo_name and repo_owner must be set")
            return None
        return f"https://{self.site}.com/{self.repo_owner}/{self.repo_name}"

    @property
    def api_base(self):
        match self.site:
            case "github":
                return "https://api.github.com"
            case _:
                raise NotImplementedError

    def set_url(self, url: str):
        """
        set repo_owner and repo_name from url
        """
        url = url.rstrip("/").lstrip(f"https://{self.site}.com/").split("/")
        assert len(url) == 2, "parsing invalid URL"
        self.repo_owner = url[0]
        self.repo_name = url[1]
        return self

    def search(self) -> Optional[list[str]]:
        """
        get the 5 top repos to download
        """
        r = requests.get(
            f"{self.api_base}/search/repositories",
            params={
                "q": f"{self.name} in:name",
                "sort": "stars",
                "per_page": OPTION_REPO_NUM,
            },
        )

        if r.status_code == 200:
            data = r.json()
            if data["items"]:
                return [x["html_url"] for x in data["items"]]
            else:
                return None

    def ask(self, quiet: bool = False):
        """
        ask what repo to install.
        please call `search()` before ask.
        """
        repo_selections = self.search()
        if not repo_selections:
            raise RepoNotFoundError
        if quiet:
            return self.set_url(repo_selections[0])
        for i, item in enumerate(repo_selections):
            print(f"{i+1}: {item['html_url']}")
        temp = input("please select a repo to download (default 1): ")
        if not temp.strip():
            temp = "1"
        return self.set_url(repo_selections[int(temp) - 1])

    def get_asset(self, prefer_gnu: bool = False, no_pre: bool = False):
        """
        get version and filter out which asset link to download
        """
        assert self.url is not None, "use ask() before get_asset"
        r = requests.get(
            f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/releases"
        ).json()
        if len(r) == 0:
            log.error("This repo has no release.")
            exit(1)
        self.version = r[0]["tag_name"]

        # check the latest 3 releases and get the asset list.
        assets: list[str]
        for i in range(min(len(r), 3)):
            assets = [x["browser_download_url"] for x in r[i]["assets"]]
            if assets:
                break

        # select
        # 1. platform
        temp = [x for x in assets if platform.system().lower() in x.lower()]
        if temp:
            assets = temp
        # 2. architecture
        temp = [x for x in assets if platform.machine().lower() in x.lower()]
        if temp:
            assets = temp
        # 3. musl or gnu
        if not prefer_gnu:
            assets = sorted(assets, key=lambda x: "musl" not in x)
        assert assets, "This repo has no available asset."
        self.asset = assets[0]
        return self


import unittest  # noqa: E402


class Test(unittest.TestCase):
    def test_search(self):
        test = RepoHadler("eza").ask(quiet=True).get_asset()
        self.assertEqual(
            test.url,
            "https://github.com/eza-community/eza",
        )
        pprint(vars(test))

    def test_sort(self):
        temp = [RepoHadler("eza"), RepoHadler("abcd"), RepoHadler("xy")]
        temp.sort()
        self.assertEqual(temp[0].name, "abcd")
        self.assertEqual(temp[1].name, "eza")
        self.assertEqual(temp[2].name, "xy")


if __name__ == "__main__":
    unittest.main()
