# gnuplot-gallery

从 gnuplot 官方演示（demo）采集整理的**现代可视化图库**：按「绘图类型 / 画面特性 / 常用指令」三大维度分类，每一张图都附带完整的 gnuplot 绘图指令，可一键复制。

项目把 **采集 → 生成 → 并入 → 预览 → 部署 → 更新** 的完整流程固化为命令行工具 `gp`，并严格用 [uv](https://docs.astral.sh/uv/) 管理依赖与虚拟环境。

- 作者：沈艺 · shenyi.box1@163.com
- 数据来源：gnuplot.info/demo
- 当前数据规模：204 个示例 / 853 张图（gnuplot 6.0.5）

---

## 特性

- **脚本化数据管线**：官网画廊采集 + 本地 gnuplot 生成，全自动产出数据。
- **仓库保持小巧**：gnuplot 工具链（约 52MB）与数据产物（约 60MB）**不进 git**，通过 `gp init` 一条命令按需重建。
- **uv 管理**：`pyproject.toml` + `uv.lock` 锁依赖，可复现安装。
- **统一 CLI**：`gp` 一个入口覆盖全流程。

---

## 目录

1. [环境要求](#1-环境要求)
2. [快速开始](#2-快速开始)
3. [命令速查表](#3-命令速查表)
4. [命令详解](#4-命令详解)
5. [部署到 Cloudflare](#5-部署到-cloudflare)
6. [更新 gnuplot 版本](#6-更新-gnuplot-版本)
7. [项目结构](#7-项目结构)
8. [数据来源与工作原理](#8-数据来源与工作原理)
9. [常见问题](#9-常见问题)

---

## 1. 环境要求

| 依赖 | 用途 | 说明 |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | 依赖 + 虚拟环境 | 必需，`uv --version` 检查 |
| Python 3.10+ | 运行时 | uv 自动下载 |
| Node.js（可选） | `gp deploy` | 有 npx 即可，wrangler 未装会自动用 npx |
| Cloudflare 账号（可选） | `gp deploy` | 部署上线需要 |

gnuplot 本身**无需手动安装**——`gp init` 会下载绿色版到 `tools/`（不进 git）。

---

## 2. 快速开始

```bash
# 1. 克隆仓库
git clone git@github.com:doladola/gnuplot-gallery.git
cd gnuplot-gallery

# 2. 用 uv 安装依赖（自动建 .venv）
uv sync

# 3. 一键初始化：下载 gnuplot 工具链 + 全量构建数据（需联网，几分钟）
uv run gp init

# 4. 本地预览
uv run gp preview --port 9000
```

打开 http://127.0.0.1:9000 即可看到图库。

> 也可以先激活虚拟环境，之后直接用 `gp`：
> ```bash
> # Windows（Git Bash / PowerShell）
> .venv\Scripts\activate
> gp status
> ```

---

## 3. 命令速查表

| 命令 | 作用 | 典型时机 |
|---|---|---|
| `gp init` | 下载工具链 + 全量构建 | 首次 clone 后 |
| `gp build` | 全量构建（fetch→generate→incorporate） | 重建数据 |
| `gp fetch` | 只采集官网画廊 | 官网画廊更新时 |
| `gp generate` | 只本地生成补充图 | 更换工具链后 |
| `gp incorporate` | 只并入数据 | 手动跑完 generate 后 |
| `gp preview [--port N]` | 本地预览 | 改动后先看效果 |
| `gp deploy [--project-name X]` | 部署到 Cloudflare Pages | 数据/前端更新后上线 |
| `gp update --version X.Y.Z` | gnuplot 大版本更新 | gnuplot 发新版时 |
| `gp tools [--version X.Y.Z]` | 只下载工具链 | 预先准备工具链 |
| `gp status` | 查看状态 | 随时 |

以上命令前均可加 `uv run`（如 `uv run gp status`），或先激活 `.venv` 后直接用 `gp`。

---

## 4. 命令详解

### `gp init` — 首次初始化

clone 后第一件事。依次完成：下载 gnuplot 工具链 → 采集官网 → 本地生成 → 并入数据。

```bash
uv run gp init
# 指定版本 / 强制重新下载工具链
uv run gp init --version 6.0.5 --force
```

### `gp build` / `gp fetch` / `gp generate` / `gp incorporate`

`build` 是前三个的串联，按依赖顺序执行，任一失败即中断：

```
fetch（采集官网 → gallery.json）→ generate（本地出图 → tools/_gen/）→ incorporate（并入 gallery.json）
```

拆开跑用于局部更新或排查：

```bash
uv run gp fetch          # 只重抓官网
uv run gp generate       # 只重新本地出图
uv run gp incorporate    # 只重新并入
```

### `gp preview` — 本地预览

起一个本地静态服务器（带 `Cache-Control: no-store`，改动即时可见）：

```bash
uv run gp preview            # http://127.0.0.1:9000
uv run gp preview --port 8080
```

按 `Ctrl+C` 停止。

### `gp tools` — 只下载工具链

```bash
uv run gp tools              # 下载 gnuplot 6.0.5 工具链到 tools/
uv run gp tools --version 6.0.5 --force
```

### `gp deploy` — 部署到 Cloudflare Pages

见 [第 5 节](#5-部署到-cloudflare)。

### `gp update` — gnuplot 大版本更新

见 [第 6 节](#6-更新-gnuplot-版本)。

---

## 5. 部署到 Cloudflare

> 背景：拖拽上传在文件很多时容易卡住，改用 CLI（wrangler）一条命令传完所有文件。

### 5.1 生成 API Token（一次性）

1. 登录 [dash.cloudflare.com](https://dash.cloudflare.com)。
2. 右上角头像 → **My Profile** → **API Tokens** → **Create Token**。
3. 选模板 **「Edit Cloudflare Workers」**，按提示创建，复制 Token（只显示一次）。

### 5.2 配置凭证（二选一）

**方式 A：写入 `.env`（推荐，已在 .gitignore 中）**

在项目根新建 `.env`：

```
CLOUDFLARE_API_TOKEN=你的token
CLOUDFLARE_ACCOUNT_ID=你的账户ID
```

> 账户 ID 在 Cloudflare 控制台右侧「Account ID」处查看；单账户可省略。

**方式 B：临时环境变量**

```bash
set CLOUDFLARE_API_TOKEN=你的token
```

### 5.3 部署

```bash
uv run gp deploy
```

wrangler 未安装时会自动用 `npx wrangler`（首次较慢）。也可提前 `npm install -g wrangler`。

### 5.4 绑定自有域名（国内可访问的关键）

默认 `*.pages.dev` 域名在大陆直连大概率打不开。绑定自有域名即可解决：

1. 域名接入 Cloudflare（Add a site，改 NS），Free 计划。
2. Pages 项目 → **Custom domains** → 添加子域名（如 `gp.你的域名.com`）。
3. Cloudflare 自动完成 CNAME + 代理 + HTTPS 证书签发。

> Cloudflare 在大陆无节点，绑定域名后国内「能稳定打开、速度中等」；要「点开即秒开」需大陆云主机 + ICP 备案（另收费）。

---

## 6. 更新 gnuplot 版本

### 6.1 官网画廊小更新

```bash
uv run gp fetch
uv run gp deploy
```

### 6.2 大版本更新（如 6.x → 7.x）

**第 1 步：下载新工具链**

```bash
uv run gp tools --version 7.0.0
```

**第 2 步：执行更新**（自动改版本号标注 + 用新版本重建）

```bash
uv run gp update --version 7.0.0
```

**第 3 步：确认并重新部署**

```bash
uv run gp status
uv run gp deploy
```

### 6.3 注意点

1. **版本号要统一**：官网采集图与本地生成图理想上是同一版本。但官网画廊 `gnuplot.info/demo` 更新常滞后于版本发布，可能出现混搭，需权衡。
2. **新 demo 要手工补归类**：`generate.py` 的 `CANDIDATES` 与 `incorporate.py` 的 `MAPPING` 里，每个 demo 都要中文名 + 归属分类，新版新增 demo 需人工判断（无法全自动）。
3. **官网换图但文件名不变时**：`fetch` 对同名已下载图片走缓存，需先删 `site/data/images/` 下对应分类目录再跑。

---

## 7. 项目结构

```
gnuplot-gallery/
├── pyproject.toml          # uv 配置：依赖 + entry point (gp)
├── uv.lock                 # 锁文件（提交）
├── .python-version         # Python 版本
├── README.md
├── .gitignore              # 排除 .venv/ tools/ site/data/
├── LICENSE
├── src/
│   └── gnuplot_gallery/    # 代码包
│       ├── __init__.py
│       ├── __main__.py     # python -m gnuplot_gallery
│       ├── cli.py          # ★ 命令行入口
│       ├── paths.py        # 路径与配置（无硬编码）
│       ├── fetch.py        # 采集官网画廊
│       ├── generate.py     # 本地 gnuplot 出图
│       ├── incorporate.py  # 并入 gallery.json
│       └── tools_setup.py  # 下载 gnuplot 工具链
├── site/                   # ★ 前端静态站（源码进 git）
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── data/               # 产物（不进 git，gp init 生成）
│       ├── gallery.json
│       └── images/
└── tools/                  # 产物（不进 git，gp tools 下载）
    ├── gnuplot-bin/        # 绿色版 exe
    ├── gnuplot-6.0.5/      # 源码包（含 demo/）
    └── _gen/               # 本地生成临时图
```

---

## 8. 数据来源与工作原理

图库数据由**两条来源**汇聚，产出 `site/data/gallery.json` + `site/data/images/`：

```
官网画廊 gnuplot.info/demo ──fetch.py──┐
                                        ├──▶ gallery.json + images ──▶ 静态站
源码包 demo/ + 绿色版 exe ──generate.py─┐
                                      ├─incorporate.py─┘
                                      （本地出图 → 并入）
```

| 来源 | 模块 | 产出 |
|---|---|---|
| 官网画廊（已渲染图，151 demo） | `fetch.py` | 下载官网图 + 抽取 `<pre>` 里的绘图指令 |
| 本地生成（源码 demo，52 demo） | `generate.py` + `incorporate.py` | 用本地 gnuplot 复刻官网 `webify` 的 `pause -1` 分段逻辑出图 |

最终 151 + 52 + test 命令 = **204 demo / 853 图**。

---

## 9. 常见问题

**Q1：`uv run gp` 报找不到 `gp`？**
先确认执行了 `uv sync`。也可以 `uv run python -m gnuplot_gallery` 代替。

**Q2：`gp init` 下载很慢或失败？**
工具链从 SourceForge 下载（约 52MB）。失败可重试；或手动下载后放到 `tools/` 对应位置，再跑 `gp build`。

**Q3：`gp generate` 生成了 0 张图？**
检查 `gp tools` 是否就位。若路径正确仍失败，多半是 `set output` 路径反斜杠问题（代码已用正斜杠处理）。

**Q4：`gp deploy` 提示缺少 Token？**
按 [5.1 / 5.2](#51-生成-api-token一次性) 配置 `.env`。

**Q5：部署成功后大陆打不开？**
默认 `*.pages.dev` 域名大陆不稳定，需绑定自有域名（见 [5.4](#54-绑定自有域名国内可访问的关键)）。

**Q6：换机器 / 移动目录后还能用吗？**
可以。整个项目无硬编码绝对路径，`uv sync && gp init` 即可在新环境重建一切。
