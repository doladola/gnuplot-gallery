# -*- coding: utf-8 -*-
"""gnuplot-gallery 命令行入口。

用法：
    gp init                        # 首次：下载工具链 + 全量构建
    gp build                       # 全量构建（fetch → generate → incorporate）
    gp fetch / generate / incorporate   # 分步执行
    gp preview [--port N]          # 本地预览
    gp deploy [--project-name X]   # 部署到 Cloudflare Pages
    gp update --version X.Y.Z      # gnuplot 大版本更新
    gp status                      # 查看状态
    gp tools [--version X.Y.Z]     # 只下载工具链
"""

import argparse
import functools
import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys

from . import commands, fetch, generate, incorporate, tools_setup
from .paths import (
    GALLERY_JSON,
    GNUPLOT_EXE,
    GNUPLOT_VERSION,
    PROJECT_ROOT,
    SITE_DIR,
)


# --------------------------------------------------------------------------- #
# 辅助函数
# --------------------------------------------------------------------------- #

def _load_env() -> dict:
    """读取项目根 .env（KEY=VALUE），不覆盖已有环境变量。"""
    out = {}
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _require_tools() -> bool:
    if tools_setup.is_ready():
        return True
    print("gnuplot 工具链未就绪。请先执行：gp init  或  gp tools")
    return False


def _update_version_labels(major_minor: str) -> None:
    """把 site/index.html 与 app.js 里的版本号标注替换为新主次版本。"""
    targets = {
        SITE_DIR / "index.html": r"gnuplot \d+\.\d+",
        SITE_DIR / "app.js": r"GNUPLOT \d+\.\d+",
    }
    for path, pattern in targets.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        new_text = re.sub(
            pattern, lambda m: m.group(0).split()[0] + " " + major_minor, text
        )
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            print(f"  已更新 {path.name} -> {major_minor}")
        else:
            print(f"  {path.name} 无需改动（已是 {major_minor}）")


def _find_wrangler():
    if shutil.which("wrangler"):
        return ["wrangler"]
    if shutil.which("npx"):
        return ["npx", "wrangler"]
    return None


# --------------------------------------------------------------------------- #
# 子命令
# --------------------------------------------------------------------------- #

def cmd_init(args):
    print("== 首次初始化：下载工具链 + 全量构建 ==")
    if not tools_setup.ensure_tools(args.version, args.force):
        return 1
    fetch.main()
    generate.main()
    incorporate.main()
    commands.main()
    print("\n初始化完成。`gp preview` 本地预览，`gp deploy` 部署上线。")
    return cmd_status(args)


def cmd_tools(args):
    return 0 if tools_setup.ensure_tools(args.version, args.force) else 1


def cmd_fetch(args):
    fetch.main()
    return 0


def cmd_generate(args):
    if not _require_tools():
        return 1
    generate.main()
    return 0


def cmd_incorporate(args):
    incorporate.main()
    return 0


def cmd_build(args):
    if not _require_tools():
        return 1
    print("== 全量构建：采集 → 生成 → 并入 → 常用指令 ==")
    fetch.main()
    generate.main()
    incorporate.main()
    commands.main()
    print("\n构建完成。")
    return cmd_status(args)


class _NoStoreHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()


def cmd_preview(args):
    port = args.port or 9000
    handler = functools.partial(_NoStoreHandler, directory=str(SITE_DIR))
    print(f"本地预览：http://127.0.0.1:{port}   （按 Ctrl+C 停止）")
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止。")
    return 0


def cmd_deploy(args):
    env = _load_env()
    token = os.environ.get("CLOUDFLARE_API_TOKEN") or env.get("CLOUDFLARE_API_TOKEN")
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or env.get("CLOUDFLARE_ACCOUNT_ID")

    if not token:
        print("缺少 Cloudflare API Token。")
        print("到 Cloudflare 后台生成（My Profile → API Tokens → Create Token →")
        print("选 'Edit Cloudflare Workers'），然后二选一：")
        print("  1) 环境变量：set CLOUDFLARE_API_TOKEN=你的token")
        print("  2) 项目根 .env 文件：CLOUDFLARE_API_TOKEN=你的token")
        return 1

    wr = _find_wrangler()
    if not wr:
        print("未找到 wrangler 或 npx。请安装 Node.js 后执行：npm install -g wrangler")
        return 1

    project = args.project_name or "gnuplot-gallery"
    cmd = wr + ["pages", "deploy", str(SITE_DIR), "--project-name", project]
    full_env = os.environ.copy()
    full_env["CLOUDFLARE_API_TOKEN"] = token
    if account:
        full_env["CLOUDFLARE_ACCOUNT_ID"] = account

    print(f"部署项目 '{project}' 到 Cloudflare Pages ...")
    print("提示：默认 *.pages.dev 域名大陆直连可能打不开，请在 Pages 后台绑定自有域名。")
    return subprocess.call(cmd, cwd=str(PROJECT_ROOT), env=full_env)


def cmd_update(args):
    new_ver = args.version.strip()
    if len(new_ver.split(".")) < 2:
        print("请提供完整版本号，例如 --version 7.0.0")
        return 1
    major_minor = ".".join(new_ver.split(".")[:2])

    print(f"== gnuplot 大版本更新：{GNUPLOT_VERSION} -> {new_ver} ==")

    if not tools_setup.is_ready(new_ver):
        print(f"\n工具链 {new_ver} 未就位。请先下载：")
        print(f"  gp tools --version {new_ver}")
        print("（下载源码包到 tools/gnuplot-{版本}/，绿色版覆盖 tools/gnuplot-bin/）")
        return 1

    print("\n== 更新版本号标注 ==")
    _update_version_labels(major_minor)

    print("\n== 用新版本重建数据 ==")
    env = os.environ.copy()
    env["GNUPLOT_VERSION"] = new_ver
    return subprocess.call(
        [sys.executable, "-m", "gnuplot_gallery.cli", "build"], env=env
    )


def cmd_status(args):
    print("=" * 56)
    print("  gnuplot-gallery 状态")
    print("=" * 56)
    if GALLERY_JSON.exists():
        data = json.loads(GALLERY_JSON.read_text(encoding="utf-8"))
        cats = data.get("categories", [])
        demos = sum(len(s.get("demos", [])) for c in cats for s in c.get("subs", []))
        figs = sum(
            len(d.get("figures", []))
            for c in cats for s in c.get("subs", []) for d in s.get("demos", [])
        )
        print(f"数据文件  : {GALLERY_JSON.relative_to(PROJECT_ROOT)}")
        print(f"图形大类  : {len(cats)}  示例 {demos}  图像 {figs}")
    else:
        print("gallery.json 不存在，请先 `gp init` 或 `gp build`")

    if tools_setup.is_ready():
        exe = str(GNUPLOT_EXE) if GNUPLOT_EXE.exists() else "gnuplot"
        try:
            r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20)
            print(f"本地 gnuplot: {r.stdout.strip()}")
        except Exception:
            print("本地 gnuplot: 已就位但无法读取版本")
    else:
        print("本地 gnuplot: 未就位（tools/，先 `gp tools` 或 `gp init`）")

    token = os.environ.get("CLOUDFLARE_API_TOKEN") or _load_env().get("CLOUDFLARE_API_TOKEN")
    print(f"部署凭证  : {'已配置' if token else '未配置'}")
    return 0


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gp",
        description="gnuplot-gallery：gnuplot 官方演示的可视化图库",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="首次：下载工具链 + 全量构建")
    p_init.add_argument("--version", default=None)
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_tools = sub.add_parser("tools", help="只下载 gnuplot 工具链")
    p_tools.add_argument("--version", default=None)
    p_tools.add_argument("--force", action="store_true")
    p_tools.set_defaults(func=cmd_tools)

    sub.add_parser("fetch", help="采集官网画廊已渲染图").set_defaults(func=cmd_fetch)
    sub.add_parser("generate", help="用本地 gnuplot 生成补充图").set_defaults(func=cmd_generate)
    sub.add_parser("incorporate", help="把本地生成的图并入 gallery.json").set_defaults(func=cmd_incorporate)
    sub.add_parser("build", help="全量构建（fetch→generate→incorporate）").set_defaults(func=cmd_build)

    p_preview = sub.add_parser("preview", help="本地预览")
    p_preview.add_argument("--port", type=int, default=9000)
    p_preview.set_defaults(func=cmd_preview)

    p_deploy = sub.add_parser("deploy", help="部署到 Cloudflare Pages")
    p_deploy.add_argument("--project-name", default="gnuplot-gallery")
    p_deploy.set_defaults(func=cmd_deploy)

    p_update = sub.add_parser("update", help="gnuplot 大版本更新")
    p_update.add_argument("--version", required=True, help="新版本号，如 7.0.0")
    p_update.set_defaults(func=cmd_update)

    sub.add_parser("status", help="查看当前状态").set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
