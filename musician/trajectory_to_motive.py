"""
将空间运动轨迹映射为音乐动机（旋律轮廓、节奏、力度）。
"""
from typing import List
from .models import TrajectoryPoint, Trajectory, Note, Motive


# 基准音高与范围（MIDI）
DEFAULT_ROOT_MIDI = 60   # C4
PITCH_RANGE = 12        # 动机在 ±12 半音内变化


def trajectory_to_motive(
    trajectory: Trajectory,
    root_midi: int = DEFAULT_ROOT_MIDI,
    pitch_range: int = PITCH_RANGE,
    base_duration: float = 0.25,
    min_velocity: float = 0.3,
    max_velocity: float = 0.95,
) -> Motive:
    """
    将轨迹转为动机。
    - 方向 (direction) → 音高走向：归一化到 [-1, 1] 后累积成音高轮廓。
    - 速度 (velocity) → 节奏：速度大则时值短，速度小则时值长。
    - 力度 (intensity) → 音符 velocity。
    """
    if not trajectory:
        return []

    # 归一化 direction 到 [-1, 1]（假设输入是角度 0~360 或任意）
    dirs = [_normalize_direction(p.direction) for p in trajectory]
    # 累积走向 → 音高偏移（半音）
    pitch_offsets = _cumulative_contour(dirs, pitch_range)

    motive: List[Note] = []
    t = 0.0
    for i, pt in enumerate(trajectory):
        # 速度 → 时值：速度大 → 时值短
        dur = _velocity_to_duration(pt.velocity, base_duration)
        # 力度 → velocity
        vel = min_velocity + pt.intensity * (max_velocity - min_velocity)
        vel = max(0, min(1, vel))
        pitch = root_midi + pitch_offsets[i]
        pitch = max(0, min(127, pitch))
        motive.append(Note(pitch=pitch, duration=dur, velocity=vel, start=t))
        t += dur
    return motive


def _normalize_direction(d: float) -> float:
    """将方向归一化到 [-1, 1]。若 d 为角度 0~360，则映射为 -1~1。"""
    # 假设 d 可能是 0~360 或 -π~π 等，统一到 -1~1
    while d > 360:
        d -= 360
    while d < 0:
        d += 360
    return (d / 360.0) * 2 - 1


def _cumulative_contour(normalized_dirs: List[float], pitch_range: int) -> List[int]:
    """将方向序列转为半音偏移序列（带范围限制）。"""
    offsets = []
    cum = 0.0
    for d in normalized_dirs:
        cum += d * 2  # 每步最多 ±2 半音
        # 限制在 ±pitch_range
        cum = max(-pitch_range, min(pitch_range, cum))
        offsets.append(round(cum))
    return offsets


def _velocity_to_duration(velocity: float, base_duration: float) -> float:
    """速度大 → 时值短；速度小 → 时值长。"""
    # velocity 0~1 → duration 约 base_duration*2 ~ base_duration*0.5
    v = max(0, min(1, velocity))
    return base_duration * (1.5 - v)
