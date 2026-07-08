# -*- coding: utf-8 -*-
"""
PyInstaller 构建脚本
生成 Windows 可执行文件
"""
import os
import sys
import shutil
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
SPEC_DIR = os.path.join(PROJECT_ROOT, "spec")

APP_NAME = "DSSAD数据提取及分析软件"


def clean():
    """清理旧的构建产物"""
    for d in [DIST_DIR, BUILD_DIR, SPEC_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"已清理: {d}")


def build():
    """执行 PyInstaller 构建"""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--clean",
        "--distpath", DIST_DIR,
        "--workpath", BUILD_DIR,
        "--specpath", SPEC_DIR,
        "--name", APP_NAME,
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'docs')}{os.pathsep}docs",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'sample_data')}{os.pathsep}sample_data",
        "--paths", SRC_DIR,
        "--collect-submodules", "numpy",
        "--collect-submodules", "cv2",
        "--collect-submodules", "pandas",
        "--collect-submodules", "pyqtgraph",
        "--collect-submodules", "openpyxl",
        "--exclude-module", "numpy.tests",
        "--exclude-module", "pandas.tests",
        "--exclude-module", "pyqtgraph.examples",
        "--hidden-import", "PyQt5.sip",
        "--hidden-import", "numpy",
        "--hidden-import", "cv2",
        "--hidden-import", "openpyxl",
        "--hidden-import", "pandas",
        "--hidden-import", "pyqtgraph",
        os.path.join(PROJECT_ROOT, "main.py")
    ]

    print("开始构建...")
    print(" ".join(cmd))
    subprocess.check_call(cmd, cwd=PROJECT_ROOT)
    print(f"构建完成，输出目录: {DIST_DIR}")


def post_build():
    """构建后处理：复制额外资源到输出目录"""
    output_app_dir = os.path.join(DIST_DIR, APP_NAME)
    if os.path.exists(output_app_dir):
        # 确保 docs 和 sample_data 已包含
        for src_name in ["docs", "sample_data"]:
            src = os.path.join(PROJECT_ROOT, src_name)
            dst = os.path.join(output_app_dir, src_name)
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copytree(src, dst)
                print(f"已复制资源: {src_name}")

        # 创建启动说明
        readme = os.path.join(DIST_DIR, "启动说明.txt")
        with open(readme, "w", encoding="utf-8") as f:
            f.write(f"双击运行 {APP_NAME}.exe 启动软件。\n")
            f.write("默认登录账号：admin / admin\n")
            f.write("详细说明见 {APP_NAME}/docs/操作手册.md\n")
        print(f"已生成启动说明: {readme}")


if __name__ == "__main__":
    clean()
    build()
    post_build()
