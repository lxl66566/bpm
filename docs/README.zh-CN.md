# bin package manager

[English](../README.md) | 简体中文

bin package manager (BPM) 是一个基于 Github release 的包管理器，它允许用户安装并管理任意 Github release 上的二进制文件。

BPM 支持 Windows 与 Linux 系统，python 版本 >= 3.9。

> [!CAUTION]
> 风险提示：BPM Linux 可能会破坏您的计算机。使用 BPM 安装软件即代表您已接受此风险，并信任第三方 Github release 的打包者。

## 为什么有这个项目？

非滚动 Linux 发行版中，官方源的软件版本常常过低，无法满足我的需求。

而滚动发行版，例如 Archlinux，也无法以 root 从 AUR 安装软件。

Windows 下的常见包管理方式是 scoop，但是其需要打包者维护一个 manifest 列表。

## 安装

BPM 需要安装到 root 用户下。

### pip

#### Linux

```sh
sudo pip install bin-package-manager --break-system-packages
sudo bpm
```

注意潜在的破坏系统包的风险。

#### Windows

```sh
pip install bin-package-manager
bpm
```

### pipx

您可以使用 pipx 安装 BPM。

```sh
sudo pipx install bin-package-manager
```

pipx 仅会为当前用户安装，因此需要使用 `sudo pipx`。或者，您可以跟踪[此 issue](https://github.com/pypa/pipx/issues/754) 并使用其中提到的方法。

### 源码

如果您不希望使用 pipx，也可以下载并使用源码。

BPM 依赖[这些库](../requirements.txt)，请手动安装。

```sh
git clone https://github.com/lxl66566/bpm.git
cd bpm
python3 -m bpm
# 或者使用 poetry 安装依赖并运行: `poetry install && poetry run python -m bpm`
```

## 使用

- 安装：`bpm i <package>`
- 执行 `bpm -h` 和 `bpm i -h`查看更多帮助。

## 原理

### Linux

BPM 自动判断 asset 中的文件结构，并安装到系统中的相应位置。目前的安装内容是：

1. 安装 binary
2. 合并 `lib`, `include`, `share`, `man`, `bin` 目录到系统
3. 安装 completions
4. 安装 services（基于 systemd 的系统）

BPM 会自动为已存在的文件添加 `.old` 后缀，以避免覆盖。卸载时，`.old` 文件将被恢复。

### Windows

BPM 下载文件夹到 `%userprofile%/bpm/app/<name>` 中，并为可执行文件创建快捷方式与 cmd 到 `%userprofile%/bpm/bin`，这个位置会被添加到 `%path%` 中。

v2.2.7 之后，单个 `.exe` 也会被安装。

## 开发

```sh
git clone https://github.com/lxl66566/bpm.git
cd bpm
poetry install  # 安装依赖
poetry run python -m unittest bpm/**/*.py  # 运行测试
```

## TODO

- [ ] no pre release
- [x] try install
- [x] windows support
- [x] offline install
- [x] install from github link
- [x] update from local
