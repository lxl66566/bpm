# bin package manager

English | [简体中文](./docs/README.zh-CN.md)

Bin package manager (BPM) is a Github release-based package manager that allows users to install and manage binaries from any Github release.

BPM is currently only supported on Linux, python >= 3.10.

> [!CAUTION]
> Risk Warning: BPM may damage your computer. By using BPM to install software, you accept this risk and trust third-party Github release packagers.

## Why use it?

In non-rolling release Linux distributions, the version of softwares in official source are often too low to use some new features.

Rolling distributions, such as Archlinux, are also unable to install software from the AUR as root.

## Installation

### pipx

You can use pipx to install BPM.

```sh
pipx install bin-package-manager
```

### Source code

If you don't want to use pipx, you can also download and use the source code.

BPM depends on Python modules: `requests`, `tqdm`, `py7zr` (optional).

```sh
git clone https://github.com/lxl66566/bpm.git
cd bpm
python3 -m bpm
# or use poetry to install dependencies and run: `poetry install && poetry run python -m bpm`
```

## Usage

- Install: `bpm i <package>`
- Run `bpm -h` for more help.

## How it works

BPM automatically determines the file structure in the asset and installs it to the appropriate location on the system. The current installation is like:

1. install binary
2. merge the `lib`, `include`, `share`, `man`, `bin` directories into the system
3. install completions

BPM automatically adds the `.old` suffix to existing files to avoid overwrite. The `.old` files will be restored in uninstalling.

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
