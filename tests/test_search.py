from bpm.search import RepoHadler


def test_search():
    assert (
        RepoHadler("eza").set(quiet=True).search().ask().url
        == "https://github.com/eza-community/eza"
    )
