"""
最小应用：从示例轨迹生成动机 → 作曲 → 播放。
"""
from musician.models import TrajectoryPoint
from musician.trajectory_to_motive import trajectory_to_motive
from musician.composer import compose
from musician.player import play_score


def make_demo_trajectory() -> list[TrajectoryPoint]:
    """构造一段示例轨迹：速度、方向、力度数组。"""
    # 模拟一段运动：先慢后快再慢，方向从 0 转到 360 再回落，力度起伏
    points = []
    for i in range(24):
        t = i / 23
        velocity = 0.3 + 0.6 * (1 - (t - 0.5) ** 2)  # 中间快
        direction = 360 * t * 0.8  # 方向变化
        intensity = 0.4 + 0.5 * (0.5 + 0.5 * __import__("math").sin(i * 0.7))
        points.append(TrajectoryPoint(velocity=velocity, direction=direction, intensity=min(1, intensity)))
    return points


def main() -> None:
    trajectory = make_demo_trajectory()
    motive = trajectory_to_motive(trajectory, base_duration=0.25)
    score = compose(motive, bpm=90, add_accompaniment=True)
    print("轨迹点数:", len(trajectory), "动机音符数:", len(motive), "BPM:", score.bpm)
    play_score(score)


if __name__ == "__main__":
    main()
