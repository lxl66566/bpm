import bisect
import pickle
from contextlib import suppress
from pathlib import Path
from pprint import pprint
from tempfile import TemporaryDirectory

from .search import RepoHadler
from .utils.constants import DATABASE_PATH, INFO_BASE_STRING
from .utils.exceptions import RepoNotFoundError


class RepoGroup:
    def __init__(self, db_path=DATABASE_PATH):
        self.repos: list[RepoHadler] = []
        self.db_path = db_path
        # read config once in the init of RepoGroup.
        self.read()

    def read(self):
        with suppress(FileNotFoundError):
            with self.db_path.open("rb") as f:
                self.repos = pickle.load(f)
        return self

    def save(self):
        with self.db_path.open("wb") as f:
            pickle.dump(self.repos, f)

    def info_repos(self):
        print(INFO_BASE_STRING.format("Name", "Url", "Version"))
        for repo in self.repos:
            print(repo)

    def info_one_repo(self, repo: str | RepoHadler) -> RepoHadler | None:
        """
        print ALL messages about one repo.
        """
        if isinstance(repo, str):
            repo = RepoHadler(repo)
        index = bisect.bisect_left(self.repos, repo)
        if index != len(self.repos) and self.repos[index].name == repo:
            pprint(vars(self.repos[index]))
            return self.repos[index]
        else:
            raise RepoNotFoundError(repo.name)

    def insert_repo(self, repo: RepoHadler):
        """
        Insert repo to RepoGroup, and save.
        """
        index = bisect.bisect_left(self.repos, repo)
        self.repos.insert(index, repo)
        self.save()


import unittest  # noqa: E402


class Test(unittest.TestCase):
    def test_insert_repo(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir) / "repos.db"
            test_group = RepoGroup(db_path=tmpdir)
            test_group.insert_repo(RepoHadler("test_repo"))
            test_group.insert_repo(RepoHadler("abc"))
            test_group.insert_repo(RepoHadler("z"))
            self.assertEqual(
                ["abc", "test_repo", "z"], [r.name for r in test_group.repos]
            )


if __name__ == "__main__":
    unittest.main()
    exit(0)
else:
    repo_group = RepoGroup()
