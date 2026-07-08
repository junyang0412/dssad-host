# -*- coding: utf-8 -*-
"""
DSSAD 读取器与本地文件读取器
支持模拟的 DSSAD 连接和本地 JSON 事件包读取
"""
import os
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from models.data import (
    VehicleInfo, Event, EventType, EventDataPoint,
    generate_sample_vehicle_info, generate_sample_events
)


class DSSADReader:
    """DSSAD 数据读取器（模拟 DoIP/UDS 读取）"""

    def __init__(self, ip: str = "192.168.1.100", port: int = 13400):
        self.ip = ip
        self.port = port
        self.connected = False
        self._vehicle_info = generate_sample_vehicle_info()
        self._events = generate_sample_events(30)

    def connect(self) -> bool:
        """模拟连接 DSSAD 设备"""
        self.connected = True
        self._vehicle_info.ip_port = f"{self.ip}:{self.port}"
        return True

    def disconnect(self):
        self.connected = False

    def get_vehicle_info(self) -> VehicleInfo:
        return self._vehicle_info

    def read_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_indices: Optional[List[int]] = None,
        event_types: Optional[List[EventType]] = None
    ) -> List[Event]:
        """按条件读取事件"""
        result = self._events[:]

        if start_date and end_date:
            result = [
                e for e in result
                if start_date <= e.start_time <= end_date
            ]

        if event_types:
            result = [e for e in result if e.event_type in event_types]

        return result

    def read_event_by_index(self, index: int) -> Optional[Event]:
        if 0 <= index < len(self._events):
            return self._events[index]
        return None

    def delete_events(self, event_ids: List[str]) -> int:
        """模拟删除 DSSAD 内部事件"""
        before = len(self._events)
        self._events = [e for e in self._events if e.id not in event_ids]
        after = len(self._events)
        return before - after


class LocalFileReader:
    """本地事件文件读取器"""

    def read_package(self, package_path: str) -> List[Event]:
        """读取本地 DSSAD 导出包目录"""
        events = []
        if not os.path.isdir(package_path):
            return events

        for name in sorted(os.listdir(package_path)):
            event_dir = os.path.join(package_path, name)
            if not os.path.isdir(event_dir):
                continue
            meta_path = os.path.join(event_dir, "metadata.json")
            if not os.path.exists(meta_path):
                continue

            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

            data_points = []
            dp_path = os.path.join(event_dir, "data_points.json")
            if os.path.exists(dp_path):
                with open(dp_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    for i, v in enumerate(raw):
                        ts = datetime.fromisoformat(meta["start_time"]) + timedelta(seconds=i)
                        data_points.append(EventDataPoint(timestamp=ts, values=v))

            event = Event(
                id=meta.get("id", name),
                name=meta.get("name", name),
                event_type=EventType(meta.get("event_type", "时间戳事件")),
                event_type_code=meta.get("event_type_code", ""),
                is_locked=meta.get("is_locked", False),
                start_time=datetime.fromisoformat(meta["start_time"]) if meta.get("start_time") else datetime.now(),
                end_time=datetime.fromisoformat(meta["end_time"]) if meta.get("end_time") else None,
                latitude=meta.get("latitude", 0.0),
                longitude=meta.get("longitude", 0.0),
                integrity_check=meta.get("integrity_check", "完整"),
                is_tampered=meta.get("is_tampered", False),
                data_points=data_points,
                video_files=meta.get("video_files", []),
                non_video_files=meta.get("non_video_files", []),
                camera_channels=meta.get("camera_channels", []),
                is_local=True,
                local_path=event_dir
            )
            events.append(event)

        return events

    def read_single_json(self, json_path: str) -> List[Event]:
        """读取单个 JSON 格式事件文件"""
        events = []
        if not os.path.exists(json_path):
            return events

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            for item in data:
                events.append(self._dict_to_event(item, json_path))
        elif isinstance(data, dict):
            events.append(self._dict_to_event(data, json_path))
        return events

    def _dict_to_event(self, item: Dict[str, Any], source_path: str) -> Event:
        st = datetime.fromisoformat(item.get("start_time", datetime.now().isoformat()))
        et = None
        if item.get("end_time"):
            et = datetime.fromisoformat(item["end_time"])

        return Event(
            id=item.get("id", "UNKNOWN"),
            name=item.get("name", "UNKNOWN"),
            event_type=EventType(item.get("event_type", "时间戳事件")),
            event_type_code=item.get("event_type_code", ""),
            is_locked=item.get("is_locked", False),
            start_time=st,
            end_time=et,
            latitude=item.get("latitude", 0.0),
            longitude=item.get("longitude", 0.0),
            integrity_check=item.get("integrity_check", "完整"),
            is_tampered=item.get("is_tampered", False),
            video_files=item.get("video_files", []),
            non_video_files=item.get("non_video_files", []),
            camera_channels=item.get("camera_channels", []),
            is_local=True,
            local_path=source_path
        )
