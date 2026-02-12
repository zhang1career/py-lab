"""
旋律数据表：轨迹→5音级 key、JSON 表加载、最长前缀查表与 fallback。
运动参数（速度、角度、力度）与调性建立联系以决定音级；key 用于查表得到主旋律。
"""
import json
import os
from typing import Any, List, Optional, Tuple, Union

from . import conf
from .models import Trajectory, Note, Motive
from .tonality import get_scale, scale_degree_to_semitone


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


# 音名字母 → 相对 C 的半音数（C=0, C#=1, ..., B=11）；C4 = MIDI 60
_KEY_ROOT_SEMITONE: dict[str, int] = {
    "c": 0, "c#": 1, "d": 2, "d#": 3, "e": 4, "f": 5, "f#": 6,
    "g": 7, "g#": 8, "a": 9, "a#": 10, "b": 11,
}


def _key_root_to_midi(note_name: str, octave: int = 4) -> int:
    """
    音名（a～g、a#～g#，大小写不敏感）转为 MIDI 音高。
    默认八度 4，即 C4=60；可传 octave 指定根音八度。
    """
    s = str(note_name).strip().lower().replace("♯", "#")
    semitone = _KEY_ROOT_SEMITONE.get(s)
    if semitone is None:
        raise ValueError(f"invalid key_root: {note_name!r}, expected a～g or a#～g#")
    return max(0, min(127, (octave + 1) * 12 + semitone))


def load_melody_table(path: Optional[str] = None) -> dict:
    """
    从 JSON 文件加载旋律表。key 为前缀字符串。
    value 为对象：{"notes": [...], "key_root": 可选(a～g/a#～g#), "KEY_MODE"/"key_mode": 可选}；
    key_root 转为 MIDI 根音（如 c→60），有则覆盖 conf 的调性。
    """
    p = path or getattr(conf, "MELODY_TABLE_PATH", None)
    if not p:
        p = os.path.join(os.path.dirname(__file__), "melody_table.json")
    if not os.path.isfile(p):
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_table_value(
    raw: dict,
    default_root_midi: int,
    default_mode: str,
) -> Tuple[List[Any], int, str]:
    """
    解析表项 value：{"notes": [...], "key_root": 可选, "KEY_MODE"/"key_mode": 可选}。
    key_root 取值为 a～g、a#～g#，会转为 MIDI（如 c→60，C4 为基准）；有则覆盖 default。
    返回 (notes_list, root_midi, mode)。
    """
    if not isinstance(raw, dict) or "notes" not in raw:
        return [], default_root_midi, default_mode
    notes_list = raw["notes"]
    # 根音：优先 key_root（字母名），否则 KEY_ROOT_MIDI（数字），否则 default
    key_root_raw = raw.get("key_root")
    if key_root_raw is not None:
        if isinstance(key_root_raw, str):
            root_midi = _key_root_to_midi(key_root_raw)
        else:
            root_midi = int(key_root_raw)
    elif raw.get("KEY_ROOT_MIDI") is not None:
        root_midi = int(raw["KEY_ROOT_MIDI"])
    else:
        root_midi = default_root_midi
    # 调式：key_mode 或 KEY_MODE 或 default
    mode_raw = raw.get("key_mode") or raw.get("KEY_MODE")
    mode = str(mode_raw) if mode_raw is not None else default_mode
    return notes_list, root_midi, mode


def _notes_from_table_value(
    raw: List[Any],
    root_midi: int,
    mode: str,
) -> Motive:
    """将表项 value（[{d, dur, vel} 或 {degree, duration, velocity}, ...]）转为 Motive（Note 列表，含 start）。"""
    notes: Motive = []
    t = 0.0
    for item in raw:
        degree = int(item.get("d", item.get("degree", 1)))
        duration = float(item.get("dur", item.get("duration", 0.5)))
        velocity = float(item.get("vel", item.get("velocity", 0.8)))
        velocity = max(0.0, min(1.0, velocity))
        pitch = _degree_to_pitch(degree, root_midi, mode)
        notes.append(Note(pitch=pitch, duration=duration, velocity=velocity, start=t))
        t += duration
    return notes


def _fallback_motive(root_midi: int, mode: str) -> Motive:
    """无表项匹配时返回的默认动机（如 1-3-5-3-1）。"""
    degrees = [1, 3, 5, 3, 1]
    return _notes_from_table_value(
        [{"d": d, "dur": 0.5, "vel": 0.8} for d in degrees],
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
            notes_list, resolved_root_midi, resolved_mode = _normalize_table_value(
                raw, root_midi, mode
            )
            if notes_list:
                return _notes_from_table_value(
                    notes_list, resolved_root_midi, resolved_mode
                )
    if use_fallback:
        return _fallback_motive(root_midi, mode)
    return []
