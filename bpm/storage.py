import bisect
import logging as log
import pickle
from contextlib import suppress
from pathlib import Path
from pprint import pprint
from tempfile import TemporaryDirectory
from typing import Optional

from .search import RepoHandler
from .utils.constants import DATABASE_PATH, INFO_BASE_STRING, WINDOWS
from .utils.exceptions import RepoNotFoundError


class RepoGroup:
    def __init__(self, db_path=DATABASE_PATH):
        self.repos: list[RepoHandler] = []
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

    def find_repo(self, repo: str | RepoHandler) -> tuple[int, Optional[RepoHandler]]:
        """
        Find a repo.
        return the index and the object of repo.
        """
        if isinstance(repo, str):
            repo = RepoHandler(repo)
        index = bisect.bisect_left(self.repos, repo)
        if index != len(self.repos) and self.repos[index] == repo:
            return (index, self.repos[index])
        return (-1, None)

    def info_one_repo(self, repo: str | RepoHandler) -> RepoHandler:
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

    def insert_repo(self, repo: RepoHandler):
        """
        Insert repo to RepoGroup, and save.
        """
        index = bisect.bisect_left(self.repos, repo)
        self.repos.insert(index, repo)
        self.save()

    def remove_repo(self, repo: str | RepoHandler) -> RepoHandler:
        """
        Remove repo and save.
        """
        index, result = self.find_repo(repo)
        if result:
            self.repos.pop(index)
            self.save()
        else:
            raise RepoNotFoundError(getattr(repo, "name", repo))

    def alias_lnk(self, old_name: str, new_name: str):
        """
        Find `old_name` in all repo_group's `file_list`, and change the lnk and cmd name to `new_name`.

        Note that the `old_name` and `new_name` should not include suffix.
        """
        assert WINDOWS, "alias is not supported on non-Windows systems."

        # only change two files: lnk, cmd
        count = 0
        for repo in self.repos:
            for i, s in enumerate(repo.installed_files):
                s = Path(s)
                assert s.exists(), "file in installed_list not found: " + s
                if s.is_dir():
                    continue
                if s.stem == old_name and s.suffix in (".lnk", ".cmd", ""):
                    new_path = s.with_stem(new_name)
                    s.replace(new_path)
                    repo.installed_files[i] = str(new_path)
                    count += 1
                    self.save()
                if count >= 3:
                    return
        log.warning(
            "You can update bpm and reinstall softwares to get cmd and sh support."
        )


import unittest  # noqa: E402


class Test(unittest.TestCase):
    def test_repogroup_operations(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir) / "repos.db"
            test_group = RepoGroup(db_path=tmpdir)
            # insert, save
            test_group.insert_repo(RepoHandler("test_repo"))
            test_group.insert_repo(RepoHandler("abc"))
            test_group.insert_repo(RepoHandler("z"))
            test_group.repos.clear()
            # read
            test_group.read()
            self.assertListEqual(
                ["abc", "test_repo", "z"], [r.name for r in test_group.repos]
            )
            # remove
            test_group.remove_repo("test_repo")
            self.assertListEqual(["abc", "z"], [r.name for r in test_group.repos])


if __name__ == "__main__":
    unittest.main()
    exit(0)
else:
    repo_group = RepoGroup()
