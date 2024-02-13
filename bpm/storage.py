import pickle
from contextlib import suppress

from constants import DATABASE_PATH, INFO_BASE_STRING
from search import RepoHadler

config: list[RepoHadler] = []


def read_config():
    global config
    with suppress(FileNotFoundError):
        with DATABASE_PATH.open("rb") as f:
            config = pickle.load(f)
    return config


# read config only once in the beginning of program.
read_config()


def write_config():
    global config
    config.sort()
    with DATABASE_PATH.open("wb") as f:
        pickle.dump(config, f)


def info_repos():
    print(INFO_BASE_STRING.format("Name", "Url", "Version"))
    for repo in config:
        print(repo)
