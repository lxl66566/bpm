import pathlib
import platform

assert platform.system() == "Linux", "This script is now for Linux only."

CONF_PATH = pathlib.Path("/etc/bpm")
DATABASE_PATH = CONF_PATH / "bpm.db"
