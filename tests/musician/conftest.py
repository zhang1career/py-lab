"""
共享 fixture 与辅助函数，供多个测试文件使用。
"""
from musician.models import TrajectoryPoint, Note


def make_trajectory(n: int):
    """构造长度为 n 的固定轨迹（可复现）。"""
    points = []
    for i in range(n):
        t = i / max(1, n - 1)
        points.append(TrajectoryPoint(
            velocity=0.3 + 0.5 * t,
            direction=360 * t * 0.7,
            intensity=0.4 + 0.4 * (t * (1 - t)),
        ))
    return points


def motive_signature(motive):
    """动机的可比较签名：(pitch 序列, duration 序列, velocity 序列)。"""
    return (
        tuple(n.pitch for n in motive),
        tuple(n.duration for n in motive),
        tuple(round(n.velocity, 4) for n in motive),
    )
