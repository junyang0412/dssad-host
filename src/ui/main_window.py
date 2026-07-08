# -*- coding: utf-8 -*-
"""
DSSAD 上位机主窗口

布局参考用户提供的 UI 示意图：
- 左上：车辆/设备基本参数区域（非交互）
- 左中：加载/读取事件文件区域（交互）
- 左下：事件列表区域（交互）
- 底部：导出/转换/删除事件区域（交互）
- 右上：视频播放区域（交互）
- 右中：视频信息区域（非交互）
- 右下：事件信息区域（非交互）
- 右底部：数据分析区域（交互）
"""
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional

import cv2
import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QImage, QPixmap, QIcon, QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QListWidget, QListWidgetItem,
    QGroupBox, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFileDialog, QMessageBox, QDialog, QProgressBar,
    QSlider, QCheckBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit,
    QSizePolicy, QMenu, QAction, QApplication, QTableView
)

from ui.login_dialog import LoginDialog
from models.data import VehicleInfo, Event, EventType, EventDataPoint
from core.reader import DSSADReader, LocalFileReader
from utils.exporter import EventExporter
from utils.helpers import format_time_ms, ensure_dir


class VideoPlayerWidget(QWidget):
    """基于 OpenCV 的视频播放器"""

    frame_changed = pyqtSignal(int, int)  # current_frame, total_frames

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_frame)
        self.video_path = ""
        self.total_frames = 0
        self.current_frame = 0
        self.fps = 30.0
        self.playback_speed = 1.0
        self.is_playing = False
        self.is_fullscreen = False

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 视频显示标签
        self.video_label = QLabel("未加载视频")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #1a1a1a; color: #888; font-size: 14px;")
        self.video_label.setMinimumSize(480, 270)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.video_label, 1)

        # 摄像头选择
        self.camera_combo = QComboBox()
        self.camera_combo.addItems(["前视摄像头", "后视摄像头", "左视摄像头", "右视摄像头", "环视合成"])
        self.camera_combo.currentIndexChanged.connect(self._on_camera_changed)

        # 播放控制
        controls = QHBoxLayout()
        self.btn_play = QPushButton("▶ 播放")
        self.btn_pause = QPushButton("⏸ 暂停")
        self.btn_step_back = QPushButton("⏮ 逐帧后退")
        self.btn_step_forward = QPushButton("⏭ 逐帧前进")
        self.btn_fullscreen = QPushButton("⛶ 全屏")

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1.0x", "2.0x", "4.0x"])
        self.speed_combo.setCurrentIndex(2)
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)

        controls.addWidget(QLabel("摄像头:"))
        controls.addWidget(self.camera_combo)
        controls.addWidget(self.btn_play)
        controls.addWidget(self.btn_pause)
        controls.addWidget(self.speed_combo)
        controls.addWidget(self.btn_step_back)
        controls.addWidget(self.btn_step_forward)
        controls.addWidget(self.btn_fullscreen)
        layout.addLayout(controls)

        # 时间轴
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderReleased.connect(self._on_slider_released)
        layout.addWidget(self.slider)

        # 时间显示
        self.time_label = QLabel("00:00:00.000 / 00:00:00.000")
        self.time_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.time_label)

        # 信号连接
        self.btn_play.clicked.connect(self.play)
        self.btn_pause.clicked.connect(self.pause)
        self.btn_step_forward.clicked.connect(self.step_forward)
        self.btn_step_back.clicked.connect(self.step_back)
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        self.video_label.mouseDoubleClickEvent = self._video_double_click

    def load_video(self, path: str):
        if not path or not os.path.exists(path):
            self.video_label.setText("视频文件不存在\n" + str(path))
            return False

        self.release()
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            self.video_label.setText("无法打开视频\n" + str(path))
            return False

        self.video_path = path
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.current_frame = 0
        self.slider.setRange(0, max(0, self.total_frames - 1))
        self.slider.setValue(0)
        self._show_frame(0)
        self._update_time_label()
        return True

    def release(self):
        self.pause()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.video_label.setText("未加载视频")
        self.time_label.setText("00:00:00.000 / 00:00:00.000")

    def play(self):
        if self.cap and not self.is_playing:
            self.is_playing = True
            interval = int(1000 / (self.fps * self.playback_speed))
            self.timer.start(max(1, interval))

    def pause(self):
        self.is_playing = False
        self.timer.stop()

    def step_forward(self):
        if self.cap and self.current_frame < self.total_frames - 1:
            self._show_frame(self.current_frame + 1)

    def step_back(self):
        if self.cap and self.current_frame > 0:
            self._show_frame(self.current_frame - 1)

    def _next_frame(self):
        if self.cap and self.is_playing:
            if self.current_frame < self.total_frames - 1:
                self._show_frame(self.current_frame + 1)
            else:
                self.pause()

    def _show_frame(self, frame_no: int):
        if not self.cap:
            return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ret, frame = self.cap.read()
        if not ret:
            return

        self.current_frame = frame_no
        self.slider.setValue(frame_no)
        self._update_time_label()

        # 缩放以适应标签
        h, w, c = frame.shape
        label_w = self.video_label.width()
        label_h = self.video_label.height()
        if label_w <= 0 or label_h <= 0:
            label_w, label_h = 640, 360
        scale = min(label_w / w, label_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        frame = cv2.resize(frame, (new_w, new_h))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        image = QImage(frame.data, new_w, new_h, new_w * c, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(pixmap)
        self.frame_changed.emit(self.current_frame, self.total_frames)

    def _update_time_label(self):
        if not self.cap or self.fps <= 0:
            return
        cur_ms = int(self.current_frame / self.fps * 1000)
        total_ms = int(self.total_frames / self.fps * 1000)
        self.time_label.setText(f"{self._fmt(cur_ms)} / {self._fmt(total_ms)}")

    def _fmt(self, ms: int) -> str:
        td = timedelta(milliseconds=ms)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        millis = ms % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"

    def _on_slider_released(self):
        if self.cap:
            self._show_frame(self.slider.value())

    def _on_speed_changed(self, text: str):
        self.playback_speed = float(text.replace("x", ""))
        if self.is_playing:
            self.timer.stop()
            interval = int(1000 / (self.fps * self.playback_speed))
            self.timer.start(max(1, interval))

    def _on_camera_changed(self, index: int):
        # 实际项目中根据摄像头切换视频文件
        self.video_label.setText(f"已切换摄像头：{self.camera_combo.currentText()}\n请加载对应视频文件")

    def _video_double_click(self, event):
        self.toggle_fullscreen()

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
            self.is_fullscreen = False
        else:
            self.showFullScreen()
            self.is_fullscreen = True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.cap and self.current_frame >= 0:
            self._show_frame(self.current_frame)


class ChartDockWidget(QWidget):
    """可移动、可关闭的数据分析图表窗口"""

    def __init__(self, title: str, event: Event, field: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Window)
        self.resize(600, 300)

        layout = QVBoxLayout(self)
        self.plot = pg.PlotWidget(title=title)
        self.plot.setLabel("left", field)
        self.plot.setLabel("bottom", "时间")
        layout.addWidget(self.plot)

        self._plot(event, field)

    def _plot(self, event: Event, field: str):
        self.plot.clear()
        if not event.data_points:
            return

        x = []
        y = []
        start = event.data_points[0].timestamp
        for dp in event.data_points:
            x.append((dp.timestamp - start).total_seconds())
            y.append(dp.values.get(field, 0))

        self.plot.plot(x, y, pen=pg.mkPen(color="#1a73e8", width=2))
        self.plot.addItem(pg.ScatterPlotItem(x=x, y=y, size=4, brush=pg.mkBrush("#1a73e8")))


class MainWindow(QMainWindow):
    """DSSAD 上位机主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DSSAD 数据提取及分析软件 v1.0")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)

        # 数据与逻辑
        self.dssad_reader = DSSADReader()
        self.local_reader = LocalFileReader()
        self.exporter = EventExporter(os.path.expanduser("~/DSSAD_Exports"))
        self.events: List[Event] = []
        self.selected_events: List[Event] = []
        self.current_event: Optional[Event] = None
        self.current_user = ("", "")
        self.chart_windows: List[QWidget] = []

        self._setup_ui()
        self._connect_signals()
        self._update_vehicle_info()
        self._refresh_event_list()

    def _setup_ui(self):
        # 菜单栏
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件")
        file_menu.addAction("打开本地事件包", self._load_local_package)
        file_menu.addAction("退出", self.close)

        help_menu = menubar.addMenu("帮助")
        help_menu.addAction("操作手册", self._show_manual)
        help_menu.addAction("关于", self._show_about)

        # 中心 widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # 顶部：车辆/设备基本参数区域
        self.gb_vehicle = QGroupBox("车辆/设备基本参数")
        self.gb_vehicle.setStyleSheet("QGroupBox { font-weight: bold; color: #1a73e8; }")
        vehicle_layout = QGridLayout(self.gb_vehicle)
        vehicle_layout.setSpacing(8)
        self.vehicle_labels = {}
        vehicle_fields = [
            ("vin", "VIN"), ("dssad_type", "DSSAD型号"), ("hardware_model", "硬件型号"),
            ("hardware_serial", "硬件序列号"), ("software_version", "软件版本号"),
            ("ip_port", "IP端口"), ("locked_info", "锁定事件"), ("collision_info", "碰撞事件"),
            ("collision_risk_info", "碰撞风险事件"), ("timestamp_info", "时间戳事件"),
            ("total_info", "总用量")
        ]
        for i, (key, text) in enumerate(vehicle_fields):
            row, col = divmod(i, 4)
            label = QLabel(f"{text}: --")
            self.vehicle_labels[key] = label
            vehicle_layout.addWidget(label, row, col)
        main_layout.addWidget(self.gb_vehicle)

        # 主体：左右分割
        h_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(h_splitter, 1)

        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # 加载/读取事件文件区域
        self.gb_load = QGroupBox("加载/读取事件文件")
        self.gb_load.setStyleSheet("QGroupBox { font-weight: bold; color: #1a73e8; }")
        load_layout = QGridLayout(self.gb_load)
        self.btn_connect_dssad = QPushButton("🚗 连接 DSSAD")
        self.btn_disconnect_dssad = QPushButton("断开连接")
        self.btn_load_from_dssad = QPushButton("📥 从 DSSAD 读取事件")
        self.btn_load_local = QPushButton("📂 读取本地事件文件")
        self.btn_load_local_package = QPushButton("📁 读取本地事件包")
        self.le_dssad_ip = QLineEdit("192.168.1.100")
        self.le_dssad_port = QLineEdit("13400")
        self.le_dssad_start = QLineEdit("2024-07-01 00:00:00")
        self.le_dssad_end = QLineEdit("2024-07-31 23:59:59")

        load_layout.addWidget(QLabel("IP:"), 0, 0)
        load_layout.addWidget(self.le_dssad_ip, 0, 1)
        load_layout.addWidget(QLabel("端口:"), 0, 2)
        load_layout.addWidget(self.le_dssad_port, 0, 3)
        load_layout.addWidget(self.btn_connect_dssad, 0, 4)
        load_layout.addWidget(self.btn_disconnect_dssad, 0, 5)
        load_layout.addWidget(QLabel("开始时间:"), 1, 0)
        load_layout.addWidget(self.le_dssad_start, 1, 1)
        load_layout.addWidget(QLabel("结束时间:"), 1, 2)
        load_layout.addWidget(self.le_dssad_end, 1, 3)
        load_layout.addWidget(self.btn_load_from_dssad, 1, 4)
        load_layout.addWidget(self.btn_load_local, 1, 5)
        load_layout.addWidget(self.btn_load_local_package, 2, 4, 1, 2)
        left_layout.addWidget(self.gb_load)

        # 事件列表区域
        self.gb_events = QGroupBox("事件列表")
        self.gb_events.setStyleSheet("QGroupBox { font-weight: bold; color: #1a73e8; }")
        event_layout = QVBoxLayout(self.gb_events)
        filter_layout = QHBoxLayout()
        self.combo_sort = QComboBox()
        self.combo_sort.addItems([
            "全部事件时间倒序", "时间戳事件时间倒序", "碰撞事件时间倒序", "碰撞风险事件时间倒序"
        ])
        self.btn_select_all = QPushButton("全选")
        self.btn_select_none = QPushButton("取消全选")
        filter_layout.addWidget(QLabel("排序:"))
        filter_layout.addWidget(self.combo_sort)
        filter_layout.addStretch()
        filter_layout.addWidget(self.btn_select_all)
        filter_layout.addWidget(self.btn_select_none)
        event_layout.addLayout(filter_layout)

        self.event_list = QListWidget()
        self.event_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        event_layout.addWidget(self.event_list)
        left_layout.addWidget(self.gb_events, 1)

        # 导出/转换/删除事件区域
        self.gb_actions = QGroupBox("导出/转换/删除事件")
        self.gb_actions.setStyleSheet("QGroupBox { font-weight: bold; color: #1a73e8; }")
        action_layout = QHBoxLayout(self.gb_actions)
        self.btn_export = QPushButton("⬇ 导出")
        self.btn_convert_excel = QPushButton("📊 转换为Excel")
        self.btn_delete = QPushButton("🗑 删除")
        self.btn_export.setStyleSheet("background-color: #1a73e8; color: white; padding: 10px;")
        self.btn_convert_excel.setStyleSheet("background-color: #188038; color: white; padding: 10px;")
        self.btn_delete.setStyleSheet("background-color: #d93025; color: white; padding: 10px;")
        action_layout.addWidget(self.btn_export)
        action_layout.addWidget(self.btn_convert_excel)
        action_layout.addWidget(self.btn_delete)
        left_layout.addWidget(self.gb_actions)

        h_splitter.addWidget(left_panel)

        # 右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # 视频播放区域
        self.gb_video = QGroupBox("视频播放区域")
        self.gb_video.setStyleSheet("QGroupBox { font-weight: bold; color: #1a73e8; }")
        video_layout = QVBoxLayout(self.gb_video)
        self.video_player = VideoPlayerWidget()
        video_layout.addWidget(self.video_player)
        right_layout.addWidget(self.gb_video, 2)

        # 视频信息区域
        self.gb_video_info = QGroupBox("视频信息")
        self.gb_video_info.setStyleSheet("QGroupBox { font-weight: bold; color: #1a73e8; }")
        video_info_layout = QGridLayout(self.gb_video_info)
        self.video_info_labels = {
            "camera": QLabel("摄像头: --"),
            "current_time": QLabel("画面当前时刻: --"),
            "start_time": QLabel("记录起点时间: --"),
            "end_time": QLabel("记录终点时间: --"),
            "duration": QLabel("总时长: --"),
            "frame": QLabel("当前帧: --"),
            "total_frames": QLabel("总帧数: --"),
            "format": QLabel("视频格式: --")
        }
        for i, (key, label) in enumerate(self.video_info_labels.items()):
            row, col = divmod(i, 4)
            video_info_layout.addWidget(label, row, col)
        right_layout.addWidget(self.gb_video_info)

        # 事件信息区域
        self.gb_event_info = QGroupBox("事件信息")
        self.gb_event_info.setStyleSheet("QGroupBox { font-weight: bold; color: #1a73e8; }")
        event_info_layout = QGridLayout(self.gb_event_info)
        self.event_info_labels = {
            "type": QLabel("事件类型: --"),
            "locked": QLabel("是否锁定: --"),
            "type_code": QLabel("事件类型编码: --"),
            "integrity": QLabel("数据完整性: --"),
            "tampered": QLabel("是否被篡改: --"),
            "latitude": QLabel("纬度: --"),
            "longitude": QLabel("经度: --"),
            "start_time": QLabel("事件起点时间: --"),
            "end_time": QLabel("事件终点时间: --")
        }
        for i, (key, label) in enumerate(self.event_info_labels.items()):
            row, col = divmod(i, 3)
            event_info_layout.addWidget(label, row, col)
        right_layout.addWidget(self.gb_event_info)

        # 数据分析区域
        self.gb_analysis = QGroupBox("数据分析区域")
        self.gb_analysis.setStyleSheet("QGroupBox { font-weight: bold; color: #1a73e8; }")
        analysis_layout = QVBoxLayout(self.gb_analysis)
        chart_control = QHBoxLayout()
        self.combo_chart_field = QComboBox()
        self.combo_chart_field.setMinimumWidth(180)
        self.btn_add_chart = QPushButton("➕ 添加图表")
        self.btn_close_all_charts = QPushButton("❌ 关闭所有图表")
        chart_control.addWidget(QLabel("纵轴数据:"))
        chart_control.addWidget(self.combo_chart_field)
        chart_control.addWidget(self.btn_add_chart)
        chart_control.addWidget(self.btn_close_all_charts)
        chart_control.addStretch()
        analysis_layout.addLayout(chart_control)
        right_layout.addWidget(self.gb_analysis)

        h_splitter.addWidget(right_panel)
        h_splitter.setSizes([400, 1000])

    def _connect_signals(self):
        self.btn_connect_dssad.clicked.connect(self._connect_dssad)
        self.btn_disconnect_dssad.clicked.connect(self._disconnect_dssad)
        self.btn_load_from_dssad.clicked.connect(self._load_from_dssad)
        self.btn_load_local.clicked.connect(self._load_local_file)
        self.btn_load_local_package.clicked.connect(self._load_local_package)
        self.btn_export.clicked.connect(self._export_events)
        self.btn_convert_excel.clicked.connect(self._convert_to_excel)
        self.btn_delete.clicked.connect(self._delete_events)
        self.btn_select_all.clicked.connect(self.event_list.selectAll)
        self.btn_select_none.clicked.connect(self.event_list.clearSelection)
        self.combo_sort.currentIndexChanged.connect(self._refresh_event_list)
        self.event_list.itemSelectionChanged.connect(self._on_event_selection_changed)
        self.btn_add_chart.clicked.connect(self._add_chart)
        self.btn_close_all_charts.clicked.connect(self._close_all_charts)
        self.video_player.frame_changed.connect(self._on_video_frame_changed)

    def _update_vehicle_info(self):
        info = self.dssad_reader.get_vehicle_info()
        self.vehicle_labels["vin"].setText(f"VIN: {info.vin}")
        self.vehicle_labels["dssad_type"].setText(f"DSSAD型号: {info.dssad_type}")
        self.vehicle_labels["hardware_model"].setText(f"硬件型号: {info.hardware_model}")
        self.vehicle_labels["hardware_serial"].setText(f"硬件序列号: {info.hardware_serial}")
        self.vehicle_labels["software_version"].setText(f"软件版本号: {info.software_version}")
        self.vehicle_labels["ip_port"].setText(f"IP端口: {info.ip_port}")
        self.vehicle_labels["locked_info"].setText(
            f"锁定事件: {info.locked_count}次, {info.locked_used}/{info.locked_max}"
        )
        self.vehicle_labels["collision_info"].setText(
            f"碰撞事件: {info.collision_count}次, {info.collision_used}/{info.collision_max}"
        )
        self.vehicle_labels["collision_risk_info"].setText(
            f"碰撞风险事件: {info.collision_risk_count}次, {info.collision_risk_used}/{info.collision_risk_max}"
        )
        self.vehicle_labels["timestamp_info"].setText(
            f"时间戳事件: {info.timestamp_count}次, {info.timestamp_used}/{info.timestamp_max}"
        )
        self.vehicle_labels["total_info"].setText(
            f"总用量: {info.total_used}/{info.total_max}"
        )

    def _connect_dssad(self):
        ip = self.le_dssad_ip.text().strip()
        port = self.le_dssad_port.text().strip()
        try:
            self.dssad_reader = DSSADReader(ip, int(port))
            ok = self.dssad_reader.connect()
        except Exception as e:
            QMessageBox.critical(self, "连接失败", f"连接 DSSAD 失败: {e}")
            return

        if ok:
            self._update_vehicle_info()
            QMessageBox.information(self, "连接成功", f"已成功连接 DSSAD\n{ip}:{port}")
        else:
            QMessageBox.critical(self, "连接失败", "无法连接 DSSAD 设备")

    def _disconnect_dssad(self):
        self.dssad_reader.disconnect()
        QMessageBox.information(self, "断开连接", "已断开 DSSAD 连接")

    def _load_from_dssad(self):
        if not self.dssad_reader.connected:
            QMessageBox.warning(self, "未连接", "请先连接 DSSAD 设备")
            return
        try:
            start = datetime.strptime(self.le_dssad_start.text().strip(), "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(self.le_dssad_end.text().strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            QMessageBox.warning(self, "时间格式错误", "请使用 yyyy-MM-dd HH:mm:ss 格式")
            return

        self.events = self.dssad_reader.read_events(start_date=start, end_date=end)
        self._refresh_event_list()
        QMessageBox.information(self, "读取完成", f"从 DSSAD 读取到 {len(self.events)} 个事件")

    def _load_local_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择本地事件文件", "", "JSON事件文件 (*.json);;所有文件 (*.*)"
        )
        if not path:
            return
        self.events = self.local_reader.read_single_json(path)
        self._refresh_event_list()
        QMessageBox.information(self, "读取完成", f"从本地读取到 {len(self.events)} 个事件")

    def _load_local_package(self):
        path = QFileDialog.getExistingDirectory(self, "选择本地事件包目录")
        if not path:
            return
        self.events = self.local_reader.read_package(path)
        self._refresh_event_list()
        QMessageBox.information(self, "读取完成", f"从本地事件包读取到 {len(self.events)} 个事件")

    def _refresh_event_list(self):
        self.event_list.clear()
        sort_mode = self.combo_sort.currentText()
        sorted_events = self.events[:]

        if sort_mode == "全部事件时间倒序":
            sorted_events.sort(key=lambda e: e.start_time, reverse=True)
        elif sort_mode == "时间戳事件时间倒序":
            sorted_events.sort(key=lambda e: (e.event_type != EventType.TIMESTAMP, e.start_time), reverse=True)
        elif sort_mode == "碰撞事件时间倒序":
            sorted_events.sort(key=lambda e: (e.event_type != EventType.COLLISION, e.start_time), reverse=True)
        elif sort_mode == "碰撞风险事件时间倒序":
            sorted_events.sort(key=lambda e: (e.event_type != EventType.COLLISION_RISK, e.start_time), reverse=True)

        for event in sorted_events:
            item = QListWidgetItem(
                f"[{event.event_type_code}] {event.name}  {event.start_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            item.setData(Qt.UserRole, event)
            self.event_list.addItem(item)

    def _on_event_selection_changed(self):
        items = self.event_list.selectedItems()
        self.selected_events = [item.data(Qt.UserRole) for item in items]

        if len(self.selected_events) == 1:
            self.current_event = self.selected_events[0]
            self._show_event_info(self.current_event)
            self._show_video_info(self.current_event)
            self._load_video_for_event(self.current_event)
            self._update_chart_fields(self.current_event)
        else:
            self.current_event = None
            self._clear_event_info()
            self._clear_video_info()

    def _show_event_info(self, event: Event):
        self.event_info_labels["type"].setText(f"事件类型: {event.type_name}")
        self.event_info_labels["locked"].setText(f"是否锁定: {'是' if event.is_locked else '否'}")
        self.event_info_labels["type_code"].setText(f"事件类型编码: {event.event_type_code}")
        self.event_info_labels["integrity"].setText(f"数据完整性: {event.integrity_check}")
        self.event_info_labels["tampered"].setText(f"是否被篡改: {'是' if event.is_tampered else '否'}")
        self.event_info_labels["latitude"].setText(f"纬度: {event.latitude:.6f}")
        self.event_info_labels["longitude"].setText(f"经度: {event.longitude:.6f}")
        self.event_info_labels["start_time"].setText(
            f"事件起点时间: {format_time_ms(event.start_time)}" if event.start_time else "事件起点时间: --"
        )
        self.event_info_labels["end_time"].setText(
            f"事件终点时间: {format_time_ms(event.end_time)}" if event.end_time else "事件终点时间: --"
        )

    def _clear_event_info(self):
        for label in self.event_info_labels.values():
            label.setText(label.text().split(":")[0] + ": --")

    def _show_video_info(self, event: Event):
        if event.event_type == EventType.TIMESTAMP or not event.end_time:
            for label in self.video_info_labels.values():
                label.setText(label.text().split(":")[0] + ": --")
            return

        self.video_info_labels["camera"].setText(f"摄像头: {event.camera_channels[0] if event.camera_channels else '前视摄像头'}")
        self.video_info_labels["start_time"].setText(f"记录起点时间: {format_time_ms(event.start_time)}")
        self.video_info_labels["end_time"].setText(f"记录终点时间: {format_time_ms(event.end_time)}")
        duration = event.duration_ms
        self.video_info_labels["duration"].setText(f"总时长: {duration / 1000:.3f}s")
        self.video_info_labels["format"].setText("视频格式: mp4")
        self.video_info_labels["current_time"].setText(f"画面当前时刻: {format_time_ms(event.start_time)}")
        self.video_info_labels["frame"].setText("当前帧: 0")
        self.video_info_labels["total_frames"].setText("总帧数: --")

    def _clear_video_info(self):
        for label in self.video_info_labels.values():
            label.setText(label.text().split(":")[0] + ": --")

    def _load_video_for_event(self, event: Event):
        # 实际项目中根据 event.video_files 加载对应视频
        # 这里生成一个模拟视频文件用于演示
        if event.event_type == EventType.TIMESTAMP or not event.video_files:
            self.video_player.release()
            self.video_player.video_label.setText("时间戳事件无视频")
            return

        # 尝试在事件目录下查找视频
        video_path = ""
        if event.is_local and event.local_path:
            for vf in event.video_files:
                candidate = os.path.join(event.local_path, vf)
                if os.path.exists(candidate):
                    video_path = candidate
                    break
        else:
            # 模拟：生成一个临时视频
            video_path = self._generate_demo_video(event)

        if video_path and os.path.exists(video_path):
            self.video_player.load_video(video_path)
        else:
            self.video_player.release()
            self.video_player.video_label.setText("未找到视频文件\n（请选择导出视频）")

    def _generate_demo_video(self, event: Event) -> str:
        """生成示例视频用于演示"""
        video_dir = os.path.expanduser("~/DSSAD_DemoVideos")
        ensure_dir(video_dir)
        video_path = os.path.join(video_dir, f"demo_{event.id}.mp4")
        if os.path.exists(video_path):
            return video_path

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(video_path, fourcc, 20.0, (640, 360))
        duration = max(1, event.duration_ms // 1000)
        for i in range(min(duration * 20, 600)):
            frame = np.zeros((360, 640, 3), dtype=np.uint8)
            # 绘制模拟道路场景
            cv2.line(frame, (0, 240), (640, 240), (128, 128, 128), 2)
            cv2.circle(frame, (320 + int(50 * np.sin(i / 10)), 240), 10, (0, 0, 255), -1)
            cv2.putText(frame, f"{event.name} Frame {i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(frame, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            out.write(frame)
        out.release()
        return video_path

    def _on_video_frame_changed(self, current_frame: int, total_frames: int):
        if self.current_event and self.current_event.start_time:
            ms_offset = int(current_frame / (self.video_player.fps or 30) * 1000)
            cur_time = self.current_event.start_time + timedelta(milliseconds=ms_offset)
            self.video_info_labels["current_time"].setText(f"画面当前时刻: {format_time_ms(cur_time)}")
            self.video_info_labels["frame"].setText(f"当前帧: {current_frame}")
            self.video_info_labels["total_frames"].setText(f"总帧数: {total_frames}")
            # 同步事件信息中的实时数据
            self._sync_event_data_to_frame(current_frame, total_frames)

    def _sync_event_data_to_frame(self, current_frame: int, total_frames: int):
        if not self.current_event or not self.current_event.data_points or total_frames <= 0:
            return
        idx = int(len(self.current_event.data_points) * current_frame / total_frames)
        idx = max(0, min(idx, len(self.current_event.data_points) - 1))
        dp = self.current_event.data_points[idx]
        # 更新实时数据标签（这里只展示部分字段，其余可在图表中查看）
        if "车辆速度_km_h" in dp.values:
            self.event_info_labels["type"].setText(
                f"事件类型: {self.current_event.type_name} | 速度: {dp.values['车辆速度_km_h']:.1f} km/h"
            )

    def _update_chart_fields(self, event: Event):
        self.combo_chart_field.clear()
        if event.data_points:
            for key in event.data_points[0].values.keys():
                self.combo_chart_field.addItem(key)

    def _add_chart(self):
        if not self.current_event:
            QMessageBox.warning(self, "未选择事件", "请先单选一个事件")
            return
        field = self.combo_chart_field.currentText()
        if not field:
            return
        title = f"{self.current_event.name} - {field}"
        chart = ChartDockWidget(title, self.current_event, field)
        self.chart_windows.append(chart)
        chart.show()

    def _close_all_charts(self):
        for w in self.chart_windows:
            w.close()
        self.chart_windows.clear()

    def _export_events(self):
        if not self.selected_events:
            QMessageBox.warning(self, "未选择事件", "请至少选择一个事件")
            return
        path = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not path:
            return
        self.exporter = EventExporter(path)
        export_dir = self.exporter.export_events(self.selected_events, self.dssad_reader.get_vehicle_info())
        QMessageBox.information(self, "导出完成", f"已导出到:\n{export_dir}")

    def _convert_to_excel(self):
        if not self.selected_events:
            QMessageBox.warning(self, "未选择事件", "请至少选择一个事件")
            return
        path = QFileDialog.getExistingDirectory(self, "选择 Excel 保存目录")
        if not path:
            return
        self.exporter = EventExporter(path)
        excel_path = self.exporter.convert_to_excel(self.selected_events)
        QMessageBox.information(self, "转换完成", f"已生成 Excel:\n{excel_path}")

    def _delete_events(self):
        if not self.selected_events:
            QMessageBox.warning(self, "未选择事件", "请至少选择一个事件")
            return

        # 权限判定
        if self.current_user[0] != "admin":
            QMessageBox.warning(self, "权限不足", "仅管理员可删除 DSSAD 内部事件")
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要从 DSSAD 内部删除 {len(self.selected_events)} 个事件吗？\n此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ids = [e.id for e in self.selected_events]
            deleted = self.dssad_reader.delete_events(ids)
            self.events = [e for e in self.events if e.id not in ids]
            self._refresh_event_list()
            self._update_vehicle_info()
            QMessageBox.information(self, "删除完成", f"已成功删除 {deleted} 个事件")

    def _show_manual(self):
        manual_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "操作手册.md")
        manual_path = os.path.abspath(manual_path)
        if os.path.exists(manual_path):
            os.startfile(manual_path)
        else:
            QMessageBox.information(self, "操作手册", "操作手册文件不存在")

    def _show_about(self):
        QMessageBox.about(
            self, "关于",
            "DSSAD 数据提取及分析软件 v1.0\n\n"
            "符合 GB 44497-2024《智能网联汽车 自动驾驶数据记录系统》\n"
            "支持 DSSAD 数据读取、视频播放、事件导出与图表分析。"
        )

    def set_current_user(self, username: str, password: str):
        self.current_user = (username, password)
