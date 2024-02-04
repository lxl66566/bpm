import lastversion as lv
import requests

from .utils import RepoNotFoundError


class RepoHadler:
    def __init__(self, name: str):
        self.name = name
        self.api_base = "https://api.github.com"
        self.data = None
        self.url = None
        self.quiet: bool = False
        self.no_pre: bool = False
        self.prefer_gnu: bool = False
        self.version = None

    def set(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        return self

    def set_url(self, url: str):
        self.url = url.rstrip("/")
        return self

    def search(self):
        r = requests.get(
            f"{self.api_base}/search/repositories",
            params={"q": f"{self.name} in:name", "sort": "stars", "per_page": 5},
        )

        if r.status_code == 200:
            data = r.json()
            if data["items"]:
                self.data = data["items"]
                return self
            else:
                return None

    def ask(self):
        """
        ask what repo to install.
        please call `search()` before ask.
        """
        if not self.data:
            raise RepoNotFoundError
        if self.quiet:
            return self.set_url(self.data[0]["html_url"])
        for i, item in enumerate(self.data):
            print(f"{i+1}: {item['html_url']}")
        temp = input("please select a repo to download (default 1): ")
        if not temp.strip():
            temp = "1"
        return self.set_url(self.data[int(temp) - 1]["html_url"])

    def get_version(self):
        assert self.url is not None, "use ask() before get_version"
        self.version = lv.latest(
            repo=self.url,
            pre_ok=not self.no_pre,
        )
        return self

    def get_asset(self):
        assert self.url is not None, "use ask() before get_asset"
        assets: list[str] = lv.latest(
            repo=self.url,
            output_format="assets",
            pre_ok=not self.no_pre,
        )
        if not self.prefer_gnu:
            assets = sorted(assets, key=lambda x: "musl" not in x)
        self.asset = assets[0]
        return self
