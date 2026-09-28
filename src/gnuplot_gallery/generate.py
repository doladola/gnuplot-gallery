# -*- coding: utf-8 -*-
"""用 gnuplot 6.0.5 批量生成官网画廊未收录的 demo 图（复刻 webify.pl 的 pause -1 分段逻辑）。"""
import os
import re
import json
import subprocess

from .paths import DEMO_DIR as _DEMO_DIR, GEN_DIR as _GEN_DIR, GNUPLOT_EXE

# gnuplot 命令：优先绿色版 exe，不存在则退回 PATH 里的 gnuplot
GNUPLOT = str(GNUPLOT_EXE) if GNUPLOT_EXE.exists() else "gnuplot"
DEMO_DIR = str(_DEMO_DIR)
# 注意：GEN_DIR 会拼进 gnuplot 的 set output，必须用正斜杠（反斜杠会被当转义符）
GEN_DIR = _GEN_DIR.as_posix()

CANDIDATES = [
    "3Dboxes", "BesselJ", "animate", "animate2", "array_index", "arrows", "arrowstyle",
    "binary_polygon", "bolditalic", "charset", "colornames", "colorscheme", "colorwheel",
    "concave_hull", "electron", "ellipses_style", "enhancedtext", "fitmulti", "fs_empty",
    "histograms2", "if_filter", "invibeta", "invigamma", "kdensity2d", "linked_autoscale",
    "log_tics", "logscale_clipping", "mask_image", "mgr", "molecule", "multipalette",
    "multiplot_mousing", "mxtics_time", "nonlinear4", "nonlinear5", "nonlinear6", "orbits",
    "palette+alpha", "polygon_border", "prob3", "probably_tux", "pt_variable", "rainbow",
    "sampling2", "short_vector", "solar_params", "special_chars", "special_functions",
    "surface_explicit", "textcolor", "textrotate", "utf8", "viridis", "watchpoints2",
    "week_date", "world2", "zsort",
]


def generate(dem_id):
    dem_path = os.path.join(DEMO_DIR, dem_id + ".dem")
    if not os.path.exists(dem_path):
        return None, f"缺文件 {dem_id}.dem"
    content = open(dem_path, encoding="utf-8", errors="ignore").read()
    lines = content.split("\n")
    out_prefix = GEN_DIR + "/" + dem_id
    os.makedirs(GEN_DIR, exist_ok=True)

    try:
        proc = subprocess.Popen([GNUPLOT], stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                cwd=DEMO_DIR, text=True, encoding="utf-8", errors="ignore")
    except Exception as e:
        return None, f"启动失败 {e}"

    try:
        proc.stdin.write("set term pngcairo size 600,400\n")
        proc.stdin.write("NO_ANIMATION = 1\n")
        plot = 1
        proc.stdin.write(f'set output "{out_prefix}.{plot}.png"\n')
        segments = []
        current = []
        for line in lines:
            if re.match(r"^\s*pause\s+-1", line):
                segments.append("\n".join(current).strip())
                current = []
                plot += 1
                proc.stdin.write(f'set output "{out_prefix}.{plot}.png"\n')
            elif re.match(r"^\s*pause", line):
                pass
            else:
                current.append(line)
                proc.stdin.write(line + "\n")
        if current:
            segments.append("\n".join(current).strip())
        proc.stdin.write("quit\n")
        proc.stdin.flush()
        proc.stdin.close()
        proc.wait(timeout=90)
    except subprocess.TimeoutExpired:
        proc.kill()
        return None, "超时"
    except Exception as e:
        try:
            proc.kill()
        except Exception:
            pass
        return None, f"异常 {e}"

    figs = []
    for i, seg in enumerate(segments, 1):
        png = f"{out_prefix}.{i}.png"
        if os.path.exists(png) and os.path.getsize(png) > 0 and seg.strip():
            figs.append({"seq": i, "script": seg})
    return figs, None


def main():
    results = {}
    for dem_id in CANDIDATES:
        figs, err = generate(dem_id)
        if err:
            print(f"[SKIP] {dem_id:24s} {err}", flush=True)
            results[dem_id] = {"status": "skip", "reason": err}
        else:
            print(f"[OK]   {dem_id:24s} {len(figs)} 图", flush=True)
            results[dem_id] = {"status": "ok", "figs": len(figs)}
    ok = sum(1 for v in results.values() if v["status"] == "ok" and v["figs"] > 0)
    print(f"\n成功: {ok}/{len(CANDIDATES)}")
    with open(os.path.join(GEN_DIR, "_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
