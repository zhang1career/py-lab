"""
数据模型：轨迹、动机、音符、乐谱。
"""
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass(frozen=True)
class TrajectoryPoint:
    """空间运动轨迹上的一个点。"""
    velocity: float   # 速度，建议 0~1
    direction: float  # 方向（如角度 0~360 或弧度），用于音高走向
    intensity: float  # 力度，建议 0~1


# 轨迹 = 一组点
Trajectory = List[TrajectoryPoint]


@dataclass
class Note:
    """一个音符事件。"""
    pitch: int        # MIDI 音高 (0-127)
    duration: float   # 时值（秒或拍）
    velocity: float   # 力度 0~1
    start: float = 0  # 开始时间（秒或拍）


# 动机 = 一条旋律线
Motive = List[Note]


@dataclass
class Track:
    """乐谱中的一条音轨。"""
    name: str
    notes: List[Note] = field(default_factory=list)


@dataclass
class Score:
    """完整乐谱：多轨。拍号仅支持 4/4。"""
    bpm: float = 120
    time_signature: Tuple[int, int] = (4, 4)
    tracks: List[Track] = field(default_factory=list)

    def total_duration(self) -> float:
        """乐谱总时长（秒）。"""
        if not self.tracks:
            return 0.0
        beat_duration = 60.0 / self.bpm
        max_end = 0.0
        for track in self.tracks:
            for n in track.notes:
                end = n.start + n.duration
                if end > max_end:
                    max_end = end
        return max_end * beat_duration
