import pathlib
import platform

match platform.system():
    case "Linux":
        CONF_PATH = pathlib.Path("/etc/bpm")
    case "Windows":
        CONF_PATH = pathlib.Path.home() / "AppData/Local/bpm"
    case _:
        raise NotImplementedError("Unsupported platform")

DATABASE_PATH = CONF_PATH / "bpm.db"
INFO_BASE_STRING = "{:20}{:50}{:20}"
OPTION_REPO_NUM = 5  # the number of repos to select in asking
