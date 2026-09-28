# -*- coding: utf-8 -*-
"""统一管理项目路径与配置。

所有模块都应从这里导入路径常量，而不是各自硬编码。这样整个项目可以
随目录移动（甚至跨机器），不会因为写死绝对路径而失效。
"""

import os
from pathlib import Path

# 项目根目录 = src/gnuplot_gallery/ 的上一级的上一级
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 前端静态站点（源码进 git；data/ 是产物，由脚本生成，不进 git）
SITE_DIR = PROJECT_ROOT / "site"
DATA_DIR = SITE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
GALLERY_JSON = DATA_DIR / "gallery.json"

# gnuplot 工具链（tools/ 不进 git，由 tools_setup 模块下载解压）
TOOLS_DIR = PROJECT_ROOT / "tools"
GNUPLOT_VERSION = os.environ.get("GNUPLOT_VERSION", "6.0.5")
GNUPLOT_SRC_DIR = TOOLS_DIR / f"gnuplot-{GNUPLOT_VERSION}"
DEMO_DIR = GNUPLOT_SRC_DIR / "demo"
# 绿色版 exe（Windows）。其它平台走 PATH 里的 gnuplot 命令。
GNUPLOT_EXE = TOOLS_DIR / "gnuplot-bin" / "gnuplot" / "bin" / "gnuplot.exe"
# 本地生成补充图的临时输出目录
GEN_DIR = TOOLS_DIR / "_gen"

# 官网画廊地址（采集数据源）
# 注意：必须用 http。www.gnuplot.info 的 https 证书 hostname 不匹配，会导致 SSL 校验失败。
DEMO_BASE_URL = "http://www.gnuplot.info/demo/"

# 下载源（SourceForge，gnuplot 6.0.5）
DOWNLOAD_BASE = "https://downloads.sourceforge.net/project/gnuplot/gnuplot"


def download_urls(version: str | None = None) -> dict:
    """返回 gnuplot 工具链两个文件的下载 URL（含文件名）。"""
    v = version or GNUPLOT_VERSION
    base = f"{DOWNLOAD_BASE}/{v}"
    return {
        "source_tarball": f"{base}/gnuplot-{v}.tar.gz",
        "windows_bin_7z": f"{base}/gp{v.replace('.', '')}-win64-mingw.7z",
    }
