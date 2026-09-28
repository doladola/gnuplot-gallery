# -*- coding: utf-8 -*-
"""生成 gnuplot `test` 命令的终端能力测试图，并入「常用指令」分类。

`test` 是 gnuplot 内置命令，输出一张展示当前终端全部线型（颜色 + 虚线）、
点型、填充样式与调色板的能力测试图。
"""

import json
import subprocess

from .paths import GALLERY_JSON, GNUPLOT_EXE, IMAGES_DIR

# 「常用指令」分类的完整结构（group=commands，前端已支持该分组）
CATEGORY = {
    "id": "commands",
    "name": "常用指令",
    "name_en": "Common Commands",
    "group": "commands",
    "subs": [
        {
            "id": "cmd",
            "name": "命令演示",
            "demos": [
                {
                    "id": "test",
                    "name": "test 命令（终端能力测试）",
                    "figures": [
                        {
                            "image": "images/commands/test.1.png",
                            "script": (
                                "# gnuplot test 命令：输出当前终端的完整能力测试图，\n"
                                "# 展示所有线型（颜色 + 虚线样式）、点型、填充样式和调色板。\n"
                                "test"
                            ),
                        }
                    ],
                }
            ],
        }
    ],
}


def generate_test_image() -> bool:
    """用 gnuplot test 命令生成 test.1.png。"""
    out = IMAGES_DIR / "commands" / "test.1.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    exe = str(GNUPLOT_EXE) if GNUPLOT_EXE.exists() else "gnuplot"
    script = (
        "set term pngcairo size 800,600\n"
        f"set output '{out.as_posix()}'\n"
        "test\n"
        "quit\n"
    )
    try:
        subprocess.run([exe], input=script, text=True, capture_output=True, timeout=60)
    except Exception:
        return False
    return out.exists() and out.stat().st_size > 0


def main() -> bool:
    """生成 test 命令图并加入 gallery.json 的「常用指令」分类。"""
    if not GALLERY_JSON.exists():
        print("[skip] gallery.json 不存在，请先 fetch")
        return False
    if not generate_test_image():
        print("[skip] test 命令图生成失败")
        return False

    data = json.loads(GALLERY_JSON.read_text(encoding="utf-8"))
    for c in data.get("categories", []):
        if c.get("id") == "commands":
            print("[skip] 常用指令分类已存在")
            return True

    data.setdefault("categories", []).append(CATEGORY)
    GALLERY_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("[OK] 常用指令分类已加入（test 命令）")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
