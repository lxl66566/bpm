class RepoNotFoundError(FileNotFoundError):
    def __init__(self, repo=""):
        super().__init__(f"Repository '{repo}' not found.")


class TarPathTraversalException(Exception):
    def __init__(self, message: str = "Tar Path exceed boundary."):
        super().__init__(message)
