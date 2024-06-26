import pathlib
import platform

WINDOWS = False
LINUX = False

if platform.system() == "Linux":
    CONF_PATH = pathlib.Path("/etc/bpm")
    LINUX = True
elif platform.system() == "Windows":
    CONF_PATH = pathlib.Path.home() / "bpm"
    WINDOWS = True
else:
    raise NotImplementedError("Unsupported platform")

DATABASE_PATH = CONF_PATH / "bpm.db"
INFO_BASE_STRING = "{:20} {:50} {:20}"
OPTION_REPO_NUM = 7  # the number of repos to select in asking

# windows only
APP_PATH = CONF_PATH / "app"
BIN_PATH = CONF_PATH / "bin"
