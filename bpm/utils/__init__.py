class RepoNotFoundError(FileNotFoundError):
    def __init__(self, repo=""):
        super().__init__(f"Repository '{repo}' not found")
