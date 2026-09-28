# -*- coding: utf-8 -*-
"""全量采集 gnuplot 官网 demo，输出三级结构 gallery.json。

分类：11 大类，两组（plots 绘图类型 / features 横切特性），
每组大类下有二级（图表类型细分），demo 整页归类。
"""
import os
import re
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .paths import DEMO_BASE_URL as BASE, DATA_DIR as _DATA_DIR, IMAGES_DIR as _IMGDIR

DATA = str(_DATA_DIR)
IMGDIR = str(_IMGDIR)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# 完整分类清单：11 大类，demo_id -> 中文名
CATEGORIES = [
    {"id": "2d", "name": "二维绘图", "name_en": "2D Plots", "group": "plots", "subs": [
        {"id": "line", "name": "折线 · 点线", "demos": [
            ("simple", "简单函数曲线"), ("steps", "阶梯图"), ("hsteps", "横向阶梯图"),
            ("using", "混合样式"), ("pointsize", "可变点大小"), ("multiaxis", "多轴刻度"),
            ("param", "参数方程"), ("piecewise", "分段函数"),
        ]},
        {"id": "fill", "name": "填充 · 面积", "demos": [
            ("fillcrvs", "填充曲线"), ("fillbetween", "曲线间填充"),
        ]},
        {"id": "error", "name": "误差棒 · K线", "demos": [
            ("errorbars", "误差棒"), ("candlesticks", "K线图"),
        ]},
        {"id": "bar", "name": "柱状 · 直方图", "demos": [
            ("histograms", "直方图"), ("histogram_colors", "直方图配色"),
            ("histerror", "直方图 + 误差棒"), ("boxclusters", "分组柱状"), ("bins", "自动分箱"),
        ]},
        {"id": "box", "name": "箱线 · 统计", "demos": [
            ("boxplot", "箱线图"), ("rugplot", "地毯图"), ("jitter", "抖动蜂群图"),
        ]},
        {"id": "vector", "name": "向量场", "demos": [
            ("vector", "向量场"),
        ]},
        {"id": "image", "name": "热力图 · 图像", "demos": [
            ("heatmaps", "热力图（网格）"), ("heatmap_points", "热力图（散点）"),
            ("polargrid", "极坐标热力"), ("binary", "二进制数据"), ("image", "图像数据"),
            ("image2", "图像技巧"), ("argb_hexdata", "RGB + alpha"), ("imageNaN", "缺失值 / NaN"),
            ("pixmap", "像素渐变图标"), ("barchart_art", "条形图艺术"),
        ]},
        {"id": "special2d", "name": "特殊二维图", "demos": [
            ("spiderplot", "蜘蛛图"), ("circles", "圆"), ("parallel", "平行坐标"), ("sectors", "扇形图"),
        ]},
    ]},
    {"id": "3d", "name": "三维绘图", "name_en": "3D Plots", "group": "plots", "subs": [
        {"id": "surface", "name": "曲面", "demos": [
            ("surface1", "曲面 1"), ("surface2", "曲面 2"), ("singulr", "奇异点"), ("hidden", "隐藏面"),
        ]},
        {"id": "contour", "name": "等高线", "demos": [
            ("contours", "等高线"), ("custom_contours", "自定义等高线"),
            ("contourfill", "填充等高线"), ("discrete", "离散等高线"),
        ]},
        {"id": "pm3d", "name": "pm3d 着色", "demos": [
            ("pm3d", "pm3d 着色曲面"), ("hidden2", "pm3d 隐藏面"), ("pm3d_clip", "pm3d 裁剪"),
            ("pm3d_lighting", "光照模型"), ("hidden_compare", "hidden3d 对比"), ("heatmap_4D", "4D 热力图"),
        ]},
        {"id": "object3d", "name": "三维对象", "demos": [
            ("boxes3d", "三维柱状"), ("armillary", "三维对象"), ("polygons", "pm3d 多边形"),
            ("projection", "三维投影"), ("zerror", "阴影误差区"), ("azimuth", "方位角"), ("spotlight", "聚光灯"),
        ]},
        {"id": "volume", "name": "等值面 · 体素", "demos": [
            ("voxel", "体素着色"), ("vplot", "体素三维表示"), ("isosurface", "三维等值面"),
        ]},
        {"id": "hull", "name": "凸包 · 掩膜", "demos": [
            ("convex_hull", "凸包"), ("mask_pm3d", "掩膜曲面"), ("chi_shapes", "凹包 χ 形"),
        ]},
    ]},
    {"id": "fitting", "name": "曲线拟合", "name_en": "Curve Fitting", "group": "plots", "subs": [
        {"id": "spline", "name": "样条", "demos": [
            ("smooth_splines", "三次 / 贝塞尔样条"), ("monotonic_spline", "单调样条"),
            ("smooth_path", "路径样条"), ("spline", "B 样条"),
        ]},
        {"id": "fit", "name": "拟合 · 逼近", "demos": [
            ("airfoil", "贝塞尔翼型"), ("fit", "最小二乘拟合"),
            ("approximate", "函数逼近"), ("sharpen", "锐化滤波"),
        ]},
    ]},
    {"id": "statistics", "name": "概率与统计", "name_en": "Probability & Statistics", "group": "plots", "subs": [
        {"id": "dist", "name": "概率分布", "demos": [
            ("prob", "概率分布"), ("prob2", "概率分布（更多）"),
        ]},
        {"id": "random", "name": "随机 · 采样", "demos": [
            ("random", "随机数"), ("bivariat", "双变量分布"),
        ]},
        {"id": "stats", "name": "统计量", "demos": [
            ("stats", "数据统计"),
        ]},
    ]},
    {"id": "special", "name": "特殊图表", "name_en": "Special Charts", "group": "plots", "subs": [
        {"id": "finance", "name": "金融 · 时序", "demos": [
            ("finance", "金融数据"), ("gantt", "甘特图"),
            ("logic_timing", "逻辑时序图"), ("rank_sequence", "序列排名"),
        ]},
        {"id": "statplots", "name": "统计图形", "demos": [
            ("violinplot", "小提琴图"), ("windrose", "风玫瑰图"),
            ("waterfallplot", "瀑布图"), ("fenceplot", "栅栏图"),
        ]},
        {"id": "geo", "name": "地图 · 地理", "demos": [
            ("map_projection", "地图投影"), ("solar_path", "太阳路径"),
        ]},
        {"id": "apps", "name": "应用案例", "demos": [
            ("epi_data", "流行病数据"), ("controls", "控制模型"), ("iterate", "迭代"),
            ("scatter", "散点数据"), ("running_avg", "移动平均"), ("smooth", "平滑"),
            ("array", "数组"), ("columnhead", "列标题"),
            ("label_stacked_histograms", "标签堆叠直方图"), ("iris", "重叠类别"),
        ]},
    ]},
    {"id": "functions", "name": "特殊函数", "name_en": "Special Functions", "group": "plots", "subs": [
        {"id": "specialfunc", "name": "特殊函数", "demos": [
            ("BesselK", "贝塞尔函数"), ("complex_trig", "复三角函数"), ("cerf", "复误差函数"),
            ("lnGamma", "复 lnGamma"), ("elliptic", "椭圆积分"), ("expint", "指数积分"),
            ("ibeta", "不完全 Beta 积分"), ("igamma", "不完全 Gamma P"),
            ("uigamma", "不完全 Gamma Q"), ("complex_airy", "艾里函数"), ("Dawson", "Dawson 积分"),
            ("Fresnel", "菲涅尔积分"), ("lambert", "朗伯 W 函数"), ("zeta", "黎曼 ζ 函数"),
            ("synchrotron", "同步辐射函数"),
        ]},
    ]},
    {"id": "colors", "name": "颜色与样式", "name_en": "Colors & Styles", "group": "features", "subs": [
        {"id": "color", "name": "数据着色", "demos": [
            ("varcolor", "数据依赖着色"), ("rgb_variable", "RGB 着色"),
            ("rgba_lines", "RGB + alpha"), ("pm3dcolors", "pm3d 颜色"),
        ]},
        {"id": "palette", "name": "调色板", "demos": [
            ("named_palettes", "命名调色板"), ("pm3dgamma", "pm3d gamma"),
        ]},
        {"id": "style", "name": "线型 · 填充", "demos": [
            ("lines_arrows", "线 / 箭头样式"), ("fillstyle", "填充样式"), ("dashtypes", "虚线样式"),
        ]},
        {"id": "alpha", "name": "透明度", "demos": [
            ("transparent", "透明"), ("transparent_solids", "透明实体"),
        ]},
    ]},
    {"id": "axes", "name": "坐标与轴", "name_en": "Axes & Coordinates", "group": "features", "subs": [
        {"id": "log", "name": "对数 · 非线性", "demos": [
            ("nonlinear2", "对数轴"), ("nonlinear3", "非线性轴"), ("nonlinear1", "断裂轴"),
        ]},
        {"id": "polar", "name": "极坐标", "demos": [
            ("polar", "极坐标函数"), ("poldat", "极坐标数据"),
            ("polar_quadrants", "极坐标象限"), ("ttics", "极坐标刻度"),
        ]},
        {"id": "axis", "name": "多轴 · 联动", "demos": [
            ("linkedaxes", "联动轴"), ("sampling", "采样范围"),
        ]},
        {"id": "time", "name": "时间 · 球面", "demos": [
            ("timedat", "时间 / 日期"), ("world", "圆柱 / 球面"),
        ]},
    ]},
    {"id": "text", "name": "文本与标注", "name_en": "Text & Labels", "group": "features", "subs": [
        {"id": "textopt", "name": "文本选项", "demos": [
            ("rotate_labels", "旋转文本"), ("enhanced_utf8", "增强文本"), ("datastrings", "字符串数据"),
            ("textbox", "文本框"), ("stringvar", "字符串变量"), ("unicode", "Unicode 字符"),
            ("cities", "文本标注"),
        ]},
    ]},
    {"id": "layout", "name": "页面布局", "name_en": "Page Layout", "group": "features", "subs": [
        {"id": "multi", "name": "多图布局", "demos": [
            ("layout", "页面布局"), ("multiplt", "多图布局"), ("margins", "对齐图"),
        ]},
        {"id": "elements", "name": "图形元素", "demos": [
            ("ellipse", "椭圆"), ("tics", "刻度"), ("walls", "墙体"),
            ("rectangle", "矩形"), ("custom_key", "自定义图例"), ("keyentry", "额外图例项"),
        ]},
    ]},
    {"id": "animation", "name": "动画与交互", "name_en": "Animation & Interaction", "group": "features", "subs": [
        {"id": "anim", "name": "动画 · 交互", "demos": [
            ("animation", "动画"), ("watchpoints", "观察点"), ("watch_contours", "三维观察点"),
        ]},
    ]},
]


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, timeout=40, headers=HEADERS)
            r.raise_for_status()
            return r
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


def parse_demo(url):
    soup = BeautifulSoup(fetch(url).text, "html.parser")
    pairs = []
    last_img = None
    body = soup.body or soup
    for el in body.find_all(["img", "pre"]):
        if el.name == "img":
            src = el.get("src", "")
            if re.search(r"\.(png|gif|webp|svg|jpg|jpeg)$", src, re.I):
                last_img = src
        elif el.name == "pre":
            # 官网在每个脚本块末尾内嵌 <p>Click here...</p> 导航链接，先移除再取文本
            for tag in el.find_all(["p", "a", "br"]):
                tag.decompose()
            code = el.get_text().strip()
            # 清理开头/结尾的空行与纯空注释行
            lines = code.split("\n")
            while lines and (not lines[0].strip() or lines[0].strip() == "#"):
                lines.pop(0)
            while lines and (not lines[-1].strip() or lines[-1].strip() == "#"):
                lines.pop()
            code = "\n".join(lines).strip()
            if code and last_img:
                pairs.append({"image": last_img, "script": code})
    return pairs


def scan_existing():
    mapping = {}
    if os.path.isdir(IMGDIR):
        for dirpath, _dirs, files in os.walk(IMGDIR):
            for f in files:
                if f.endswith((".png", ".gif", ".webp", ".svg", ".jpg", ".jpeg")):
                    mapping.setdefault(f, os.path.join(dirpath, f))
    return mapping


def download(imgurl, abspath, existing):
    if os.path.exists(abspath) and os.path.getsize(abspath) > 0:
        return "cached"
    base = os.path.basename(abspath)
    if base in existing and os.path.getsize(existing[base]) > 0:
        with open(existing[base], "rb") as src, open(abspath, "wb") as dst:
            dst.write(src.read())
        return "reused"
    r = fetch(imgurl, tries=2)
    with open(abspath, "wb") as f:
        f.write(r.content)
    return "ok"


def main():
    os.makedirs(IMGDIR, exist_ok=True)
    existing = scan_existing()
    result = {"meta": {"source": BASE, "generated": time.strftime("%Y-%m-%d %H:%M:%S")},
              "categories": []}

    for cat in CATEGORIES:
        cdir = os.path.join(IMGDIR, cat["id"])
        os.makedirs(cdir, exist_ok=True)
        cat_out = {"id": cat["id"], "name": cat["name"],
                   "name_en": cat["name_en"], "group": cat["group"], "subs": []}
        print(f"\n== {cat['name']} ({cat['name_en']}) ==", flush=True)

        for sub in cat["subs"]:
            sub_out = {"id": sub["id"], "name": sub["name"], "demos": []}
            for demo_id, demo_zh in sub["demos"]:
                try:
                    pairs = parse_demo(urljoin(BASE, demo_id + ".html"))
                except Exception as e:
                    print(f"  [FAIL] {demo_id}: {e}", flush=True)
                    continue
                if not pairs:
                    print(f"  [EMPTY] {demo_id}: 未解析到图", flush=True)
                    continue

                jobs = []
                for idx, p in enumerate(pairs, 1):
                    fname = os.path.basename(p["image"])
                    abspath = os.path.join(cdir, fname)
                    imgurl = urljoin(BASE, p["image"])
                    jobs.append((idx, fname, imgurl, abspath, p["script"]))

                figures = []
                with ThreadPoolExecutor(max_workers=6) as ex:
                    futs = {ex.submit(download, j[2], j[3], existing): j for j in jobs}
                    for fut in as_completed(futs):
                        j = futs[fut]
                        try:
                            fut.result()
                            figures.append({"image": f"images/{cat['id']}/{j[1]}",
                                            "script": j[4]})
                        except Exception as e:
                            print(f"    [IMG FAIL] {j[2]} -> {e}", flush=True)

                if not figures:
                    print(f"  [NOIMG] {demo_id}: 图全部下载失败", flush=True)
                    continue
                figures.sort(key=lambda f: int(re.search(r"\.(\d+)\.", f["image"]).group(1))
                             if re.search(r"\.(\d+)\.", f["image"]) else 0)
                sub_out["demos"].append({"id": demo_id, "name": demo_zh,
                                         "figures": figures})
                print(f"  [{sub['name']}] {demo_id:20s} {len(figures)} figs", flush=True)
            cat_out["subs"].append(sub_out)
        result["categories"].append(cat_out)

    out = os.path.join(DATA, "gallery.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    n_demos = sum(len(s["demos"]) for c in result["categories"] for s in c["subs"])
    n_figs = sum(len(d["figures"]) for c in result["categories"]
                 for s in c["subs"] for d in s["demos"])
    print(f"\nDONE: {len(result['categories'])} categories, "
          f"{n_demos} demos, {n_figs} figures -> {out}", flush=True)


if __name__ == "__main__":
    main()
