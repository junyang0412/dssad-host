# -*- coding: utf-8 -*-
"""
登录认证对话框
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt


class LoginDialog(QDialog):
    """用户登录对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DSSAD 上位机 - 登录认证")
        self.setFixedSize(400, 220)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("DSSAD 数据提取及分析软件")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a73e8;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("请输入用户名和密码以继续操作")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("用户名")
        self.username_input.setText("admin")
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setText("admin")
        layout.addWidget(self.password_input)

        btn_layout = QHBoxLayout()
        self.btn_login = QPushButton("登 录")
        self.btn_login.setDefault(True)
        self.btn_login.setStyleSheet(
            "QPushButton { background-color: #1a73e8; color: white; padding: 8px 24px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #1557b0; }"
        )
        self.btn_cancel = QPushButton("取 消")
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_login)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.btn_login.clicked.connect(self._on_login)
        self.btn_cancel.clicked.connect(self.reject)

    def _on_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "输入错误", "用户名和密码不能为空")
            return

        # 简单身份认证：生产环境应连接后端或 LDAP/AD
        if username == "admin" and password == "admin":
            self.accept()
        else:
            QMessageBox.warning(self, "认证失败", "用户名或密码错误")

    def get_credentials(self):
        return self.username_input.text().strip(), self.password_input.text().strip()
