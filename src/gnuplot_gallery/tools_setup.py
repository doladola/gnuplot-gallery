# -*- coding: utf-8 -*-
"""下载 gnuplot 工具链（绿色版 exe + 源码包）并解压到 tools/。

tools/ 目录不进 git，clone 后通过 `gp init` 或 `gp tools` 按需下载。

- 源码包 gnuplot-X.Y.Z.tar.gz → 用 Python 标准库 tarfile 解压
- 绿色版 gpXXX-win64-mingw.7z（仅 Windows）→ 用系统自带的 bsdtar 解压
"""

import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import requests

from .paths import (
    GNUPLOT_EXE,
    GNUPLOT_VERSION,
    TOOLS_DIR,
    download_urls,
)

CHUNK = 1 << 16  # 64 KB


def _download(url: str, dest: Path, label: str) -> None:
    """流式下载并打印进度。"""
    print(f"  下载 {label} ...")
    print(f"    {url}")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=CHUNK):
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    print(
                        f"\r    {pct:3d}%  ({done / 1048576:6.1f}/{total / 1048576:.1f} MB)",
                        end="", flush=True,
                    )
        if total:
            print()


def _extract_tarball(archive: Path, dest: Path) -> None:
    print(f"  解压 {archive.name} ...")
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tf:
        tf.extractall(dest)


def _extract_7z(archive: Path, dest: Path) -> None:
    """解压 .7z。优先 Windows 系统 bsdtar（libarchive 支持 7z），其次 7-Zip。"""
    dest.mkdir(parents=True, exist_ok=True)
    # Windows 系统自带 tar.exe（bsdtar），支持读取 7z
    systemroot = os.environ.get("SystemRoot", r"C:\Windows")
    system_tar = os.path.join(systemroot, "System32", "tar.exe")
    if os.path.exists(system_tar):
        print(f"  解压 {archive.name} (系统 tar) ...")
        subprocess.run([system_tar, "-xf", str(archive), "-C", str(dest)], check=True)
        return
    # 兜底：7-Zip 命令行
    if shutil.which("7z"):
        print(f"  解压 {archive.name} (7-Zip) ...")
        subprocess.run(["7z", "x", str(archive), f"-o{dest}", "-y"], check=True)
        return
    raise RuntimeError("无法解压 .7z：需要 Windows 系统 tar 或已安装的 7-Zip")


def is_ready(version: str | None = None) -> bool:
    """工具链是否已就位。"""
    v = version or GNUPLOT_VERSION
    src_ready = (TOOLS_DIR / f"gnuplot-{v}" / "demo").is_dir()
    if os.name == "nt":
        bin_ready = GNUPLOT_EXE.exists()
        return src_ready and bin_ready
    # 非 Windows：源码包就绪即可（gnuplot 走系统 PATH）
    return src_ready


def ensure_tools(version: str | None = None, force: bool = False) -> bool:
    """确保工具链就位，缺则下载解压。返回是否就绪。"""
    v = version or GNUPLOT_VERSION
    urls = download_urls(v)

    if is_ready(v) and not force:
        print(f"gnuplot {v} 工具链已就位，跳过下载。")
        return True

    print(f"准备 gnuplot {v} 工具链 → {TOOLS_DIR}")
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 源码包（含 demo/ 脚本目录）
    src_dir = TOOLS_DIR / f"gnuplot-{v}"
    tarball = TOOLS_DIR / f"gnuplot-{v}.tar.gz"
    if not tarball.exists() or force:
        _download(urls["source_tarball"], tarball, "源码包")
    if not (src_dir / "demo").is_dir():
        _extract_tarball(tarball, TOOLS_DIR)

    # 2. 绿色版 exe（仅 Windows）
    if os.name == "nt":
        bin_dir = TOOLS_DIR / "gnuplot-bin"
        sevenz = TOOLS_DIR / Path(urls["windows_bin_7z"]).name
        if not sevenz.exists() or force:
            _download(urls["windows_bin_7z"], sevenz, "绿色版 exe")
        if not GNUPLOT_EXE.exists():
            _extract_7z(sevenz, bin_dir)
    else:
        print("  提示：非 Windows 平台请自行安装 gnuplot，并确保 `gnuplot` 在 PATH 中。")

    print("工具链就绪。")
    return is_ready(v)


def main() -> int:
    """CLI 入口：gp tools [--version X.Y.Z] [--force]。"""
    import argparse

    parser = argparse.ArgumentParser(description="下载 gnuplot 工具链到 tools/")
    parser.add_argument("--version", default=None, help="gnuplot 版本号，默认 6.0.5")
    parser.add_argument("--force", action="store_true", help="强制重新下载")
    args = parser.parse_args()
    return 0 if ensure_tools(args.version, args.force) else 1


if __name__ == "__main__":
    raise SystemExit(main())
