from pathlib import Path
from tempfile import TemporaryDirectory

from pretty_assert import assert_eq

from bpm.search import RepoHandler
from bpm.storage import RepoGroup


class TestStorage:
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
            assert_eq(["abc", "test_repo", "z"], [r.name for r in test_group.repos])
            # remove
            test_group.remove_repo("test_repo")
            assert_eq(["abc", "z"], [r.name for r in test_group.repos])
