# -*- coding: utf-8 -*-
"""
DSSAD 数据提取及分析软件
主入口

项目结构：
  dssad-host/
    main.py
    src/
      ui/
      core/
      models/
      utils/
"""
import sys
import os

# 将 src 目录加入 Python 路径
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 登录认证
    login = LoginDialog()
    if login.exec_() != LoginDialog.Accepted:
        return 0

    username, password = login.get_credentials()

    # 主窗口
    window = MainWindow()
    window.set_current_user(username, password)
    window.showMaximized()
    window.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
