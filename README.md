# bin package manager

English | [简体中文](./docs/README.zh-CN.md)

Bin package manager (BPM) is a Github release-based package manager that allows users to install and manage binaries from any Github release.

BPM is currently supported on Linux and Windows, python >= 3.10.

> [!CAUTION]
> Risk Warning: BPM on Linux may damage your computer. By using BPM to install software, you accept this risk and trust third-party Github release packagers.

## Why use it?

In non-rolling release Linux distributions, the version of softwares in official source are often too low to use some new features.

Rolling distributions, such as Archlinux, are also unable to install software from the AUR as root.

A common way to manage packages on Windows is scoop, but it requires the packager to maintain a "manifest" list.

## Installation

BPM needs to be installed to root user.

### pip

#### Linux

```sh
sudo pip install bin-package-manager --break-system-packages
sudo bpm
```

Note the risk of potentially breaking system packages.

#### Windows

```sh
pip install bin-package-manager
bpm
```

### pipx

You can use pipx to install BPM.

```sh
sudo pipx install bin-package-manager
```

pipx will only install for the current user, so `sudo` is required. Alternatively, you can track on [this issue](https://github.com/pypa/pipx/issues/754) and use other methods mentioned there.

### Source code

If you don't want to use pipx, you can also download and use the source code.

BPM requires [these libs](./requirements.txt), please install them manually.

```sh
git clone https://github.com/lxl66566/bpm.git
cd bpm
python3 -m bpm
# or use poetry to install dependencies and run: `poetry install && poetry run python -m bpm`
```

## Usage

- Install: `bpm i <package>`
- Run `bpm -h` and `bpm i -h` for more help.

```
❯ bpm i -h
usage: bpm install [-h] [-b [BIN_NAME]] [-l [Archive]] [-q] [--one-bin] [--prefer-gnu] [-n] [-i] [--sort [SORT]] packages [packages ...]

positional arguments:
  packages              Package name or github url to install

options:
  -h, --help            show this help message and exit
  -b [BIN_NAME], --bin-name [BIN_NAME]
                        specify the binary executable filename, otherwise use package name by default.
  -l [Archive], --local [Archive]
                        install from local archive.
  -q, --quiet           not ask, install the best match repo.
  --one-bin             install given binary only. Use package name as binary name by default.
  --prefer-gnu          bpm prefers musl target by default, you can change this default option.
  -n, --dry-run         print the install position, but not install actually.
  -i, --interactive     select asset interactively.
  --sort [SORT]         sort param in github api, use `best-match` by default. The value could be `stars`, `forks`, `help-wanted-
                        issues`, `updated`.
```

## How it works

### Linux

BPM automatically determines the file structure in the asset and installs it to the appropriate location on the system. The current installation is like:

1. install binary
2. merge the `lib`, `include`, `share`, `man`, `bin` directories into the system
3. install completions

BPM automatically adds the `.old` suffix to existing files to avoid overwrite. The `.old` files will be restored in uninstalling.

### Windows

BPM downloads asset into `%userprofile%/bpm/app/<name>` and creates shortcuts and cmd runner for the executables to `%userprofile%/bpm/bin`, which is added to `%path%`.

## Develop

```sh
git clone https://github.com/lxl66566/bpm.git
cd bpm
poetry install
poetry run python -m unittest bpm/**/*.py  # run tests
```

## TODO

- [ ] no pre release
- [x] try install
- [x] windows support
- [x] offline install
- [x] install from github link
- [x] update from local
