import bisect
import pickle
from contextlib import suppress
from pathlib import Path
from pprint import pprint
from tempfile import TemporaryDirectory
from typing import Optional

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
            self.repos = pickle.loads(self.db_path.read_bytes())
        return self

    def save(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path.write_bytes(pickle.dumps(self.repos))

    def info_repos(self):
        print(INFO_BASE_STRING.format("Name", "Url", "Version"))
        for repo in self.repos:
            print(repo)

    def find_repo(self, repo: str | RepoHadler) -> tuple[int, Optional[RepoHadler]]:
        """
        Find a repo.
        return the index and the object of repo.
        """
        if isinstance(repo, str):
            repo = RepoHadler(repo)
        index = bisect.bisect_left(self.repos, repo)
        if index != len(self.repos) and self.repos[index] == repo:
            return (index, self.repos[index])
        return (-1, None)

    def info_one_repo(self, repo: str | RepoHadler) -> RepoHadler:
        """
        Print ALL messages about one repo.
        If not found, raise exception `RepoNotFoundError`.
        """
        _, result = self.find_repo(repo)
        if result:
            pprint(vars(result))
            return result
        else:
            raise RepoNotFoundError(getattr(repo, "name", repo))

    def insert_repo(self, repo: RepoHadler):
        """
        Insert repo to RepoGroup, and save.
        """
        index = bisect.bisect_left(self.repos, repo)
        self.repos.insert(index, repo)
        self.save()

    def remove_repo(self, repo: str | RepoHadler) -> RepoHadler:
        """
        Remove repo and save.
        """
        index, result = self.find_repo(repo)
        if result:
            self.repos.pop(index)
            self.save()
        else:
            raise RepoNotFoundError(getattr(repo, "name", repo))


import unittest  # noqa: E402


class Test(unittest.TestCase):
    def test_repogroup_operations(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir) / "repos.db"
            test_group = RepoGroup(db_path=tmpdir)
            # insert, save
            test_group.insert_repo(RepoHadler("test_repo"))
            test_group.insert_repo(RepoHadler("abc"))
            test_group.insert_repo(RepoHadler("z"))
            test_group.repos.clear()
            # read
            test_group.read()
            self.assertEqual(
                ["abc", "test_repo", "z"], [r.name for r in test_group.repos]
            )
            # remove
            test_group.remove_repo("test_repo")
            self.assertEqual(["abc", "z"], [r.name for r in test_group.repos])


if __name__ == "__main__":
    unittest.main()
    exit(0)
else:
    repo_group = RepoGroup()
