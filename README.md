# DSSAD 数据提取及分析软件

> 基于 **GB 44497-2024**《智能网联汽车 自动驾驶数据记录系统》标准的 L3+ 自动驾驶数据记录上位机软件

## 简介

本软件用于读取、展示、导出和分析 DSSAD（Data Storage System for Automated Driving）设备中存储的事件数据。支持通过 DoIP/UDS 协议连接 DSSAD 设备或从本地文件加载事件包，提供视频播放、数据可视化、Excel 导出等功能，适用于自动驾驶安全评估与测试场景。

## 功能特性

### 8 大功能区域

| 区域 | 功能 |
|------|------|
| 车辆参数 | VIN、车牌、DSSAD 类型（I/II 型）、存储容量等 |
| 加载/读取事件 | DoIP/UDS 连接 DSSAD 设备 / 读取本地事件包 |
| 事件列表 | 排序、多选，显示事件类型、时间、触发原因 |
| 导出/转换/删除 | 导出事件包目录、Excel 汇总转换、删除权限判定（仅 admin） |
| 视频播放 | OpenCV 多路摄像头切换、0.25x~4x 倍速、逐帧、时间轴拖拽、全屏 |
| 视频信息 | 与视频帧同步显示对应时间点的事件数据 |
| 事件信息 | 选中事件后显示详细数据点表格 |
| 数据分析 | pyqtgraph 实现 10+ 张图表（速度、加速度、方向盘转角、踏板开度等） |

### 其他特性

- 身份认证：登录后使用，默认账号 `admin` / `admin`
- 事件类型：锁定事件、碰撞事件、碰撞风险事件、时间戳事件
- 数据完整性校验：哈希计算功能
- 示例数据：内置 2 个示例事件，开箱即用

## 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| PyQt5 | 5.15.11 | GUI 框架 |
| OpenCV | 4.11.0 | 视频解码与播放 |
| pyqtgraph | 0.13.7 | 数据可视化图表 |
| openpyxl | 3.1.5 | Excel 导出 |
| pandas | 2.2.3 | 数据处理 |
| PyInstaller | 6.13.0 | 打包为 exe |

## 项目结构

```
dssad-host/
├── main.py                  # 程序入口
├── build.py                 # PyInstaller 构建脚本
├── requirements.txt         # 依赖清单
├── .gitignore
├── docs/
│   ├── 操作手册.md          # 用户操作手册
│   └── 架构说明.md          # 架构设计文档
├── sample_data/             # 示例事件数据
│   ├── vehicle_info.json
│   ├── EVT-0001/            # 碰撞事件示例
│   └── EVT-0002/            # 碰撞风险事件示例
└── src/
    ├── models/data.py       # 数据模型（EventType, Event, VehicleInfo...）
    ├── core/reader.py       # DSSADReader + LocalFileReader
    ├── ui/login_dialog.py   # 登录窗口
    ├── ui/main_window.py    # 主窗口 + VideoPlayerWidget + ChartDockWidget
    └── utils/
        ├── helpers.py       # 工具函数
        └── exporter.py      # 事件导出 + Excel 转换
```

## 快速开始

### 环境要求

- Python 3.10+
- Windows 7+ / 10 / 11（32/64 位）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行

```bash
python main.py
```

登录账号：`admin` / `admin`

### 打包为 exe

```bash
python build.py
```

输出：`dist/DSSAD数据提取及分析软件/DSSAD数据提取及分析软件.exe`

## 使用示例

1. 启动软件，使用 `admin` / `admin` 登录
2. 点击「读取本地文件」加载 `sample_data/` 目录中的示例事件
3. 在事件列表中选择事件，查看事件详情和视频
4. 播放视频，观察与视频帧同步的事件数据
5. 在数据分析区域选择字段，添加图表进行可视化分析
6. 选择事件后可导出为目录结构或转换为 Excel

## 架构设计

软件采用四层架构：

```
UI 层（PyQt5）→ 业务逻辑层（Reader/Exporter）→ 数据模型层（data.py）→ 工具层（utils）
```

详细架构说明请参考 [docs/架构说明.md](docs/架构说明.md)。

## 待完善

- [ ] 真实 DSSAD 设备 DoIP/UDS 协议对接（当前为模拟实现）
- [ ] 真实视频文件格式适配
- [ ] 数据完整性校验 UI 展示
- [ ] 多语言支持（英文界面）
- [ ] Windows 7 兼容性测试

## 标准

- **GB 44497-2024**《智能网联汽车 自动驾驶数据记录系统》

## License

MIT
