class RepoNotFoundError(FileNotFoundError):
    def __init__(self, repo=""):
        super().__init__(
            f"""Repository{(" '" + repo + "'") if repo else ""} not found."""
        )


class InvalidAssetError(FileNotFoundError):
    """
    Has assets, but cannot filter out a valid asset.
    """

    def __init__(self):
        super().__init__(
            "No available asset found in this repo. If you're sure there's a valid asset, use `--interactive`."
        )


class AssetNotFoundError(FileNotFoundError):
    """
    No assets.
    """

    def __init__(self):
        super().__init__("This repo has no assets.")


class TarPathTraversalException(Exception):
    def __init__(self, message: str = "Tar Path exceed boundary."):
        super().__init__(message)


class LnkNotFoundError(FileNotFoundError):
    def __init__(self, lnk_name: str = ""):
        super().__init__(
            f"""Lnk {(" '" + lnk_name + "'") if lnk_name else ""} not found."""
        )
