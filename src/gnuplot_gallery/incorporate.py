# -*- coding: utf-8 -*-
"""把本地 gnuplot 生成的第 4 类 demo 图并入 gallery.json。"""
import os
import re
import json
import glob
import shutil

from .paths import DATA_DIR as _DATA_DIR, IMAGES_DIR as _IMGDIR, GEN_DIR as _GEN_DIR, DEMO_DIR as _DEMO_DIR

DATA = str(_DATA_DIR)
IMGDIR = str(_IMGDIR)
GEN_DIR = str(_GEN_DIR)
DEMO_DIR = str(_DEMO_DIR)

# demo_id -> (category, sub, 中文名)
MAPPING = {
    "3Dboxes": ("3d", "object3d", "三维箱体"),
    "BesselJ": ("functions", "specialfunc", "贝塞尔 J 函数"),
    "animate": ("animation", "anim", "动画"),
    "animate2": ("animation", "anim", "动画（更多）"),
    "arrows": ("2d", "special2d", "箭头"),
    "arrowstyle": ("2d", "special2d", "箭头样式"),
    "binary_polygon": ("2d", "image", "二进制多边形"),
    "bolditalic": ("text", "textopt", "粗斜体"),
    "charset": ("text", "textopt", "字符集"),
    "colornames": ("colors", "palette", "颜色名"),
    "colorscheme": ("colors", "palette", "配色方案"),
    "concave_hull": ("3d", "hull", "凹包"),
    "electron": ("3d", "object3d", "电子轨道"),
    "ellipses_style": ("2d", "special2d", "椭圆样式"),
    "enhancedtext": ("text", "textopt", "增强文本"),
    "fs_empty": ("special", "apps", "空数据集"),
    "histograms2": ("2d", "bar", "直方图（更多）"),
    "if_filter": ("special", "apps", "条件过滤"),
    "invibeta": ("functions", "specialfunc", "反不完全 Beta"),
    "invigamma": ("functions", "specialfunc", "反不完全 Gamma"),
    "kdensity2d": ("statistics", "random", "二维核密度"),
    "linked_autoscale": ("axes", "axis", "联动自动缩放"),
    "log_tics": ("axes", "log", "对数刻度"),
    "logscale_clipping": ("axes", "log", "对数裁剪"),
    "mask_image": ("2d", "image", "图像掩膜"),
    "mgr": ("3d", "object3d", "分子图形"),
    "molecule": ("3d", "object3d", "分子模型"),
    "multipalette": ("3d", "pm3d", "多调色板"),
    "multiplot_mousing": ("animation", "anim", "多图鼠标交互"),
    "mxtics_time": ("axes", "time", "分钟刻度"),
    "nonlinear4": ("axes", "log", "非线性轴（4）"),
    "nonlinear5": ("axes", "log", "非线性轴（5）"),
    "nonlinear6": ("axes", "log", "非线性轴（6）"),
    "orbits": ("3d", "object3d", "天体轨道"),
    "palette+alpha": ("colors", "color", "调色板 + alpha"),
    "polygon_border": ("2d", "special2d", "多边形边框"),
    "prob3": ("statistics", "dist", "概率分布（更多）"),
    "probably_tux": ("special", "apps", "企鹅"),
    "pt_variable": ("colors", "style", "可变点类型"),
    "rainbow": ("colors", "palette", "彩虹调色板"),
    "sampling2": ("axes", "axis", "采样（更多）"),
    "short_vector": ("2d", "vector", "短向量场"),
    "special_chars": ("text", "textopt", "特殊字符"),
    "special_functions": ("functions", "specialfunc", "特殊函数集"),
    "surface_explicit": ("3d", "surface", "显式曲面"),
    "textcolor": ("text", "textopt", "文本颜色"),
    "textrotate": ("text", "textopt", "文本旋转"),
    "utf8": ("text", "textopt", "UTF-8"),
    "viridis": ("colors", "palette", "Viridis 调色板"),
    "watchpoints2": ("animation", "anim", "观察点（更多）"),
    "world2": ("axes", "time", "世界球面"),
    "zsort": ("3d", "surface", "Z 轴排序"),
}


def split_dem(content):
    segments = []
    current = []
    for line in content.split("\n"):
        if re.match(r"^\s*pause\s+-1", line):
            segments.append("\n".join(current).strip())
            current = []
        elif re.match(r"^\s*pause", line):
            pass
        else:
            current.append(line)
    if current:
        segments.append("\n".join(current).strip())
    return segments


def main():
    gallery = json.load(open(DATA + "/gallery.json", encoding="utf-8"))

    # 建立 category/sub 索引
    cat_map = {c["id"]: c for c in gallery["categories"]}
    sub_map = {}
    for c in gallery["categories"]:
        for s in c["subs"]:
            sub_map[(c["id"], s["id"])] = s

    added_demos = 0
    added_figs = 0
    skipped = []

    for demo_id, (cat_id, sub_id, zh) in sorted(MAPPING.items()):
        dem_path = DEMO_DIR + "/" + demo_id + ".dem"
        if not os.path.exists(dem_path):
            skipped.append(demo_id)
            continue
        content = open(dem_path, encoding="utf-8", errors="ignore").read()
        segments = split_dem(content)

        pngs = sorted(glob.glob(GEN_DIR + "/" + demo_id + ".*.png"))
        figures = []
        for png in pngs:
            if os.path.getsize(png) == 0:
                continue
            m = re.search(r"\.(\d+)\.png$", png)
            seq = int(m.group(1))
            seg = segments[seq - 1] if seq - 1 < len(segments) else ""
            seg = seg.strip()
            if not seg:
                continue
            dest = f"{IMGDIR}/{cat_id}/{demo_id}.{seq}.png"
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy(png, dest)
            figures.append({"image": f"images/{cat_id}/{demo_id}.{seq}.png", "script": seg})

        if not figures:
            skipped.append(demo_id + "(无有效图)")
            continue

        sub = sub_map[(cat_id, sub_id)]
        sub["demos"].append({"id": demo_id, "name": zh, "figures": figures})
        added_demos += 1
        added_figs += len(figures)

    # 写回（处理文件锁）
    out = DATA + "/gallery.json"
    try:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(gallery, f, ensure_ascii=False, indent=2)
        print("写入成功")
    except PermissionError:
        os.remove(out)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(gallery, f, ensure_ascii=False, indent=2)
        print("删旧后写入成功")

    print(f"新增 demo: {added_demos}, 新增图: {added_figs}")
    if skipped:
        print("跳过:", skipped)


if __name__ == "__main__":
    main()
