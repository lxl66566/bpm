import logging as log
import platform
from functools import reduce
from pprint import pprint
from typing import Optional
from urllib.parse import urlparse

import requests

from .utils.constants import INFO_BASE_STRING, OPTION_REPO_NUM, WINDOWS
from .utils.exceptions import AssetNotFoundError, RepoNotFoundError


class RepoHandler:
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.bin_name = name
        self.site = "github"
        self.repo_name = None
        self.repo_owner = None
        self.asset = None
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

    def set(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    def with_bin_name(self, bin_name: str | None):
        if WINDOWS:
            self.bin_name = bin_name.rstrip(".exe") + ".exe" if bin_name else "*.exe"
        else:
            self.bin_name = bin_name or self.name
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

    def set_url(self, url: str):
        """
        set repo_owner and repo_name from url
        """
        # why does https://t.me/withabsolutex/1479 happens?
        r = urlparse(url).path.strip("/").split("/")
        assert len(r) == 2, "parsing invalid URL"
        self.repo_owner = r[0]
        self.repo_name = r[1]
        return self

    def search(self, page=1) -> Optional[list[str]]:
        """
        get the 5 top repos to download
        """
        r = requests.get(
            f"{self.api_base}/search/repositories",
            params={
                "q": f"{self.name} in:name",
                "sort": "stars",
                "page": page,
                "per_page": OPTION_REPO_NUM,
            },
        )

        if r.status_code == 200:
            data = r.json()
            if data["items"]:
                return [x["html_url"] for x in data["items"]]
            else:
                raise RepoNotFoundError
        else:
            r.raise_for_status()

    def ask(self, quiet: bool = False):
        """
        ask what repo to install.
        please call `search()` before ask.
        """
        page = 1
        while True:
            repo_selections = self.search(page)
            if not repo_selections:
                raise RepoNotFoundError
            if quiet:
                log.info(f"auto select repo: {repo_selections[0]}")
                return self.set_url(repo_selections[0])
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
                return self.set_url(repo_selections[int(temp) - 1])
            except KeyboardInterrupt:
                print("Canceled.")
                exit(0)
            except IndexError:
                print(
                    f"Invalid input: the number should not be more than {OPTION_REPO_NUM}"
                )
                exit(1)
            except ValueError:
                print("Invalid input: please input a valid number.")
                exit(1)

    def get_asset(self):
        """
        get version and filter out which asset link to download
        """
        assert self.url is not None, "use ask() before get_asset"
        api = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/releases"
        r: list = requests.get(api).json()
        log.debug(f"asset api: {api}")
        if not isinstance(r, list):
            log.error(f"repo {self.repo_owner}/{self.repo_name} not found.")
            raise RepoNotFoundError

        r = r[:25]  # only gets the front 25 results.
        r = list(filter(lambda x: bool(x["assets"]), r))
        if len(r) == 0:
            raise AssetNotFoundError

        self.version = r[0]["tag_name"]
        assets: list[str] = [x["browser_download_url"] for x in r[0]["assets"]]

        # select
        # 1. platform
        temp = [x for x in assets if platform.system().lower() in x.lower()]
        if temp:
            assets = temp
        # windows maybe use `win` instead of `windows`
        elif WINDOWS and "win" not in self.name.lower():
            assets = [x for x in assets if "win" in x.lower()]
            if not assets:
                raise AssetNotFoundError
        # 2. architecture
        temp = [x for x in assets if platform.machine().lower() in x.lower()]
        if temp:
            assets = temp
        # 3. musl or gnu
        if not self.prefer_gnu:
            assets = sorted(assets, key=lambda x: "musl" not in x)
        # 4. tar, zip, 7z, other
        assets = sorted(assets, key=lambda x: not x.endswith(".7z"))
        if WINDOWS:
            assets = sorted(assets, key=lambda x: ".tar." not in x)
            assets = sorted(assets, key=lambda x: not x.endswith(".zip"))
        else:
            assets = sorted(assets, key=lambda x: not x.endswith(".zip"))
            assets = sorted(assets, key=lambda x: ".tar." not in x)

        if not assets:
            raise AssetNotFoundError
        self.asset = assets[0]
        log.info(f"selected asset: {self.asset}")
        return self

    def update_asset(self) -> Optional[tuple[str, str]]:
        """
        update assets list.

        `Returns`: `None` if has no update, `(old_version, new_version)` if has update.
        """
        old_version = self.version
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
        self.assertEqual(test.file_list, ["a", "b", "c"])

    def test_parse_url(self):
        test = RepoHandler("yazi").set_url("https://github.com/sxyazi/yazi")
        self.assertEqual(test.repo_owner, "sxyazi")
        self.assertEqual(test.repo_name, "yazi")


if __name__ == "__main__":
    unittest.main()
