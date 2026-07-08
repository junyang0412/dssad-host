# -*- coding: utf-8 -*-
"""
DSSAD 数据模型定义
符合 GB 44497-2024《智能网联汽车 自动驾驶数据记录系统》
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Any, Optional


class EventType(Enum):
    """事件类型"""
    LOCKED = "锁定事件"
    COLLISION = "碰撞事件"
    COLLISION_RISK = "碰撞风险事件"
    TIMESTAMP = "时间戳事件"


class DSSADType(Enum):
    """DSSAD 类型"""
    TYPE_I = "I型"
    TYPE_II = "II型"


@dataclass
class VehicleInfo:
    """车辆/设备基本参数"""
    vin: str = ""
    dssad_type: str = "I型"
    hardware_model: str = ""
    hardware_serial: str = ""
    software_version: str = ""
    ip_port: str = ""
    # 存储统计
    locked_count: int = 0
    locked_used: str = "0M"
    locked_max: str = "10G"
    collision_count: int = 0
    collision_used: str = "0M"
    collision_max: str = "10G"
    collision_risk_count: int = 0
    collision_risk_used: str = "0M"
    collision_risk_max: str = "10G"
    timestamp_count: int = 0
    timestamp_used: str = "0M"
    timestamp_max: str = "10G"
    total_used: str = "0M"
    total_max: str = "30G"


@dataclass
class EventDataPoint:
    """事件数据点（按时间序列）"""
    timestamp: datetime
    values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Event:
    """事件记录"""
    id: str
    name: str
    event_type: EventType
    event_type_code: str
    is_locked: bool
    start_time: datetime
    end_time: Optional[datetime]
    latitude: float
    longitude: float
    integrity_check: str = "完整"
    is_tampered: bool = False
    data_points: List[EventDataPoint] = field(default_factory=list)
    video_files: List[str] = field(default_factory=list)
    non_video_files: List[str] = field(default_factory=list)
    camera_channels: List[str] = field(default_factory=list)
    is_local: bool = False
    local_path: str = ""

    @property
    def duration_ms(self) -> int:
        if self.end_time:
            return int((self.end_time - self.start_time).total_seconds() * 1000)
        return 0

    @property
    def type_name(self) -> str:
        return self.event_type.value


@dataclass
class DSSADPackage:
    """DSSAD 导出包"""
    vehicle_info: VehicleInfo
    events: List[Event]
    export_time: datetime = field(default_factory=datetime.now)


def generate_sample_vehicle_info() -> VehicleInfo:
    """生成示例车辆信息"""
    return VehicleInfo(
        vin="LSVAG2180E2100001",
        dssad_type="I型",
        hardware_model="DSSAD-HW-2024",
        hardware_serial="HW202406010001",
        software_version="V2.1.3-R20240601",
        ip_port="192.168.1.100:13400",
        locked_count=5,
        locked_used="120M",
        locked_max="10G",
        collision_count=3,
        collision_used="300M",
        collision_max="10G",
        collision_risk_count=12,
        collision_risk_used="800M",
        collision_risk_max="10G",
        timestamp_count=48,
        timestamp_used="50M",
        timestamp_max="10G",
        total_used="1.27G",
        total_max="30G",
    )


def generate_sample_events(count: int = 20) -> List[Event]:
    """生成示例事件数据"""
    events = []
    base_time = datetime(2024, 7, 12, 14, 0, 0)
    import random
    for i in range(count):
        etype = random.choice([
            EventType.COLLISION,
            EventType.COLLISION_RISK,
            EventType.TIMESTAMP,
            EventType.LOCKED
        ])
        start = base_time + timedelta(seconds=i)
        end = start + timedelta(seconds=15) if etype != EventType.TIMESTAMP else None
        data_points = []
        if end:
            for j in range(15):
                t = start + timedelta(seconds=j)
                data_points.append(EventDataPoint(
                    timestamp=t,
                    values={
                        "车辆速度_km_h": random.uniform(0, 120),
                        "车辆横向加速度_m_s2": random.uniform(-5, 5),
                        "车辆纵向加速度_m_s2": random.uniform(-8, 8),
                        "加速踏板开度比例_%": random.uniform(0, 100),
                        "刹车踏板开度比例_%": random.uniform(0, 100),
                        "方向盘转角_度": random.uniform(-180, 180),
                        "横摆角速度_deg_s": random.uniform(-30, 30),
                    }
                ))
        event = Event(
            id=f"EVT-{i+1:04d}",
            name=f"{etype.value}_{i+1:03d}_{start.strftime('%Y%m%d%H%M%S')}",
            event_type=etype,
            event_type_code={
                EventType.LOCKED: "LCK",
                EventType.COLLISION: "COL",
                EventType.COLLISION_RISK: "CRK",
                EventType.TIMESTAMP: "TSP"
            }[etype],
            is_locked=etype == EventType.LOCKED,
            start_time=start,
            end_time=end,
            latitude=31.2304 + random.uniform(-0.01, 0.01),
            longitude=121.4737 + random.uniform(-0.01, 0.01),
            integrity_check="完整",
            is_tampered=False,
            data_points=data_points,
            video_files=["front.mp4"] if etype != EventType.TIMESTAMP else [],
            non_video_files=["data.json"],
            camera_channels=["前视摄像头"] if etype != EventType.TIMESTAMP else []
        )
        events.append(event)
    return events
