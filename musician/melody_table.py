"""
旋律数据表：轨迹→5音级 key、JSON 表加载、最长前缀查表与 fallback。
运动参数（速度、角度、力度）与调性建立联系以决定音级；key 用于查表得到主旋律。
"""
import json
import os
from typing import Any, List, Optional, Tuple, Union

from . import conf
from .models import TrajectoryPoint, Trajectory, Note, Motive
from .tonality import get_scale, scale_degree_to_semitone, snap_pitch_to_scale


# 音级 1–7 对应音阶内第一八度；查表 value 中 degree 为 1–7
def _degree_to_pitch(degree: int, root_midi: int, mode: str) -> int:
    """音级 1–7（第一八度）转为 MIDI。"""
    semitone = scale_degree_to_semitone((degree - 1) % 7, mode)
    octave = (degree - 1) // 7
    return max(0, min(127, root_midi + octave * 12 + semitone))


def _normalize_direction(d: float) -> float:
    """方向归一化到 [-1, 1]。"""
    while d > 360:
        d -= 360
    while d < 0:
        d += 360
    return (d / 360.0) * 2 - 1


def trajectory_to_key(
    trajectory: Trajectory,
    root_midi: int,
    mode: str,
    key_length: int = 5,
) -> Tuple[int, ...]:
    """
    运动轨迹 → 固定长度 key（音级 1–7）。
    通过运动参数（速度、角度、力度）与调性建立联系：在轨迹上采样 key_length 个位置，
    用方向映射轮廓、速度/力度影响选音，得到调内音级序列。
    """
    key_len = max(1, min(7, key_length))
    if not trajectory:
        return (1,) * key_len
    n = len(trajectory)
    if n == 1:
        d = _normalize_direction(trajectory[0].direction)
        scale_idx = max(0, min(6, int(3 + d * 3)))
        return tuple((scale_idx + 1,) * key_len)
    # 均匀采样 key_len 个位置（时间维度）
    indices = [0] if key_len == 1 else [int(i * (n - 1) / (key_len - 1)) for i in range(key_len)]
    cum = 3.0  # 从音阶中部开始，0–6 对应 1–7
    scale = get_scale(mode)
    degrees: List[int] = []
    for i, idx in enumerate(indices):
        p = trajectory[min(idx, n - 1)]
        d = _normalize_direction(p.direction)
        # 方向→轮廓步长；速度/力度加权
        weight = 0.5 + 0.5 * max(0, min(1, p.velocity)) * max(0, min(1, p.intensity))
        step = d * 1.5 * weight
        cum += step
        cum = max(0.0, min(6.0, cum))
        scale_idx = int(round(cum)) % 7
        degrees.append(scale_idx + 1)
    return tuple(degrees)


def key_to_string(key: Union[Tuple[int, ...], List[int]]) -> str:
    """音级序列转为表 key 字符串，如 '1,3,5,3,1'。"""
    return ",".join(str(d) for d in key)


def load_melody_table(path: Optional[str] = None) -> dict:
    """从 JSON 文件加载旋律表。key 为前缀字符串，value 为旋律（音符列表，每音 degree/duration/velocity）。"""
    p = path or getattr(conf, "MELODY_TABLE_PATH", None)
    if not p:
        p = os.path.join(os.path.dirname(__file__), "melody_table.json")
    if not os.path.isfile(p):
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _notes_from_table_value(
    raw: List[Any],
    root_midi: int,
    mode: str,
) -> Motive:
    """将表项 value（[{degree, duration, velocity}, ...]）转为 Motive（Note 列表，含 start）。"""
    notes: Motive = []
    t = 0.0
    for item in raw:
        degree = int(item.get("degree", 1))
        duration = float(item.get("duration", 0.5))
        velocity = float(item.get("velocity", 0.8))
        velocity = max(0.0, min(1.0, velocity))
        pitch = _degree_to_pitch(degree, root_midi, mode)
        notes.append(Note(pitch=pitch, duration=duration, velocity=velocity, start=t))
        t += duration
    return notes


def _fallback_motive(root_midi: int, mode: str) -> Motive:
    """无表项匹配时返回的默认动机（如 1-3-5-3-1）。"""
    degrees = [1, 3, 5, 3, 1]
    return _notes_from_table_value(
        [{"degree": d, "duration": 0.5, "velocity": 0.8} for d in degrees],
        root_midi,
        mode,
    )


def lookup_melody(
    key: Union[Tuple[int, ...], List[int], str],
    root_midi: int,
    mode: str,
    table_path: Optional[str] = None,
    use_fallback: bool = True,
) -> Motive:
    """
    按 key（音级序列或字符串）最长前缀查表，返回 Motive。
    若无匹配则 use_fallback 时返回默认旋律，否则返回空列表。
    """
    if isinstance(key, str):
        key_tuple = tuple(int(x.strip()) for x in key.split(",") if x.strip())
    else:
        key_tuple = tuple(key)
    table = load_melody_table(table_path)
    # 最长前缀：从全长到 1
    for length in range(len(key_tuple), 0, -1):
        prefix = key_tuple[:length]
        k = key_to_string(prefix)
        if k in table:
            raw = table[k]
            if isinstance(raw, list) and raw:
                return _notes_from_table_value(raw, root_midi, mode)
    if use_fallback:
        return _fallback_motive(root_midi, mode)
    return []
