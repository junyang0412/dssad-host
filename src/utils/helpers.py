# -*- coding: utf-8 -*-
"""
通用工具函数
"""
import os
import json
import hashlib
from datetime import datetime
from typing import Any, Dict


def format_time_ms(dt: datetime) -> str:
    """格式化为毫秒级时间字符串（UTC+8）"""
    return dt.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt.microsecond // 1000:03d}"


def format_size(size_str: str) -> str:
    """格式化存储容量字符串"""
    return size_str


def parse_size(size_str: str) -> int:
    """解析容量字符串为字节数"""
    size_str = size_str.upper().strip()
    units = {"B": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    for unit, factor in units.items():
        if unit in size_str:
            try:
                return int(float(size_str.replace(unit, "")) * factor)
            except ValueError:
                return 0
    try:
        return int(size_str)
    except ValueError:
        return 0


def compute_hash(data: Any) -> str:
    """计算数据完整性校验码"""
    s = json.dumps(data, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def ensure_dir(path: str) -> str:
    """确保目录存在"""
    if not os.path.exists(path):
        os.makedirs(path)
    return path
