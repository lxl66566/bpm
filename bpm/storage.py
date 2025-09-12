import bisect
import json
import logging as log
import pickle
from pathlib import Path
from pprint import pprint
from typing import Optional, Union

from pretty_assert import assert_

from .search import RepoHandler
from .utils.constants import DATABASE_PATH, INFO_BASE_STRING, OLD_DATABASE_PATH, WINDOWS
from .utils.exceptions import RepoNotFoundError


class RepoGroup:
    def __init__(self, db_path=DATABASE_PATH):
        self.repos: list[RepoHandler] = []
        self.db_path = db_path
        # read config once in the init of RepoGroup.
        self.read()

    def read(self):
        try:
            try:
                self.repos = list(
                    map(RepoHandler.from_dict, json.loads(self.db_path.read_text()))
                )
            except (json.JSONDecodeError, UnicodeDecodeError, FileNotFoundError):
                log.info("fallback to pickle")
                self.repos = pickle.loads(OLD_DATABASE_PATH.read_bytes())
        except FileNotFoundError:
            log.warning("database not found. use a clean database instead.")
        return self

    def save(self):
        log.info(f"save db to {self.db_path}")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # self.db_path.write_bytes(pickle.dumps(self.repos))
        self.db_path.write_text(
            json.dumps(list(map(lambda x: x.to_dict(), self.repos)))
        )

    def info_repos(self):
        print(INFO_BASE_STRING.format("Name", "Url", "Version"))
        for repo in self.repos:
            print(repo)

    def find_repo(
        self, repo: Union[str, RepoHandler]
    ) -> tuple[int, Optional[RepoHandler]]:
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

    def info_one_repo(self, repo: Union[str, RepoHandler]) -> RepoHandler:
        """
        Print ALL messages about one repo.
        If not found, raise exception `RepoNotFoundError`.
        """
        _, result = self.find_repo(repo)
        if result:
            pprint(vars(result))
            return result
        else:
            raise RepoNotFoundError(str(getattr(repo, "name", repo)))

    def insert_repo(self, repo: RepoHandler):
        """
        Insert repo to RepoGroup, and save.
        """
        index = bisect.bisect_left(self.repos, repo)
        self.repos.insert(index, repo)
        self.save()

    def remove_repo(self, repo: Union[str, RepoHandler]) -> RepoHandler:
        """
        Remove repo and save.
        """
        index, result = self.find_repo(repo)
        if result:
            res = self.repos.pop(index)
            self.save()
            return res
        else:
            raise RepoNotFoundError(str(getattr(repo, "name", repo)))

    def alias_lnk(self, old_name: str, new_name: str):
        """
        Find `old_name` in all repo_group's `file_list`, and change the lnk and cmd name to `new_name`.

        Note that the `old_name` and `new_name` should not include suffix.
        """
        assert WINDOWS, "alias is not supported on non-Windows systems."

        # change three files: lnk, cmd, ""
        count = 0
        for repo in self.repos:
            for i, s in enumerate(repo.installed_files):
                s = Path(s)
                assert_(s.exists(), f"file in installed_list not found: {s}")  # type: ignore
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


repo_group = RepoGroup()  # singleton
