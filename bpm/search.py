import logging as log
from pprint import pprint

import requests
from utils import RepoNotFoundError


class RepoHadler:
    def __init__(self, name: str):
        self.name = name
        self.site = "github"
        self.repo_name = None
        self.repo_owner = None
        self.repo_selections = None
        self.asset = None
        self.quiet: bool = False
        self.no_pre: bool = False
        self.prefer_gnu: bool = False
        self.version = None

    def set(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    @property
    def url(self):
        assert (
            self.repo_name and self.repo_owner
        ), "repo_name and repo_owner must be set"
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

    def search(self):
        r = requests.get(
            f"{self.api_base}/search/repositories",
            params={"q": f"{self.name} in:name", "sort": "stars", "per_page": 5},
        )

        if r.status_code == 200:
            data = r.json()
            if data["items"]:
                self.repo_selections = [x["html_url"] for x in data["items"]]
                return self
            else:
                return None

    def ask(self):
        """
        ask what repo to install.
        please call `search()` before ask.
        """
        if not self.repo_selections:
            raise RepoNotFoundError
        if self.quiet:
            return self.set_url(self.repo_selections[0])
        for i, item in enumerate(self.repo_selections):
            print(f"{i+1}: {item['html_url']}")
        temp = input("please select a repo to download (default 1): ")
        if not temp.strip():
            temp = "1"
        return self.set_url(self.repo_selections[int(temp) - 1])

    def get_asset(self):
        """
        get version and filter out asset link of the repo
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

        if not self.prefer_gnu:
            assets = sorted(assets, key=lambda x: "musl" not in x)
        self.asset = assets[0]
        return self


import unittest  # noqa: E402


class TestRepoHadler(unittest.TestCase):
    def test_search(self):
        test = RepoHadler("eza").set(quiet=True).search().ask().get_asset()
        self.assertEqual(
            test.url,
            "https://github.com/eza-community/eza",
        )
        pprint(vars(test))


if __name__ == "__main__":
    unittest.main()
