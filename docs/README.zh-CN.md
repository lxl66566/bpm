# bin package manager

[English](../README.md) | 简体中文

bin package manager (BPM) 是一个基于 Github release 的包管理器，它允许用户安装并管理任意 Github release 上的二进制文件。

BPM 当前仅支持 Linux 系统。

> [!CAUTION]
> 风险提示：BPM 可能会破坏您的计算机。使用 BPM 安装软件即代表您已接受此风险，并信任第三方 Github release 的打包者。

## 为什么有这个项目？

非滚动 Linux 发行版中，官方源的软件版本常常过低，无法满足我的需求。

而滚动发行版，例如 Archlinux，也无法以 root 从 AUR 安装软件。

## 安装

### pipx

您可以使用 pipx 安装 BPM。

```sh
pipx install bin-package-manager
```

### 源码

如果您不希望使用 pipx，也可以下载并使用源码。

BPM 依赖 Python 模块：`requests`, `tqdm`，`py7zr`（可选的）。

```sh
git clone https://github.com/lxl66566/bpm.git
cd bpm
python3 -m bpm
# 或者使用 poetry 安装依赖并运行: `poetry install && poetry run python -m bpm`
```

## 使用

- 安装：`bpm i <package>`
- 执行 `bpm -h` 查看更多帮助。

## 原理

BPM 自动判断 asset 中的文件结构，并安装到系统中的相应位置。目前的安装内容是：

1. 安装 binary
2. 合并 `lib`, `include`, `share`, `man`, `bin` 目录到系统
3. 安装 completions

BPM 会自动为已存在的文件添加 `.old` 后缀，以避免覆盖。卸载时，`.old` 文件将被恢复。

## 开发

```sh
git clone https://github.com/lxl66566/bpm.git
cd bpm
poetry install  # 安装依赖
poetry run python -m unittest bpm/**/*.py  # 运行测试
```

## TODO

- [ ] no pre release
- [ ] try install
