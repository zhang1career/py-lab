"""
最小应用：从示例轨迹生成动机 → 作曲 → 播放。
"""
import math
import os
import random
import time
from musician import conf
from musician.models import TrajectoryPoint, Note
from musician.trajectory_to_motive import trajectory_to_motive
from musician.composer import compose
from musician.player import play_score


def make_demo_trajectory(length: int = conf.DEMO_TRAJECTORY_LENGTH) -> list[TrajectoryPoint]:
    """构造一段示例轨迹：速度、方向、力度数组。"""
    points = []
    n = length - 1
    for i in range(length):
        t = i / n if n > 0 else 1
        velocity = conf.DEMO_VELOCITY_LO + conf.DEMO_VELOCITY_HI_SPAN * (1 - (t - 0.5) ** 2)
        direction = 360 * t * conf.DEMO_DIRECTION_SCALE
        intensity = conf.DEMO_INTENSITY_LO + conf.DEMO_INTENSITY_HI_SPAN * (0.5 + 0.5 * math.sin(i * conf.DEMO_INTENSITY_SIN_FREQ))
        points.append(TrajectoryPoint(velocity=velocity, direction=direction, intensity=min(1.0, intensity)))
    return points


def main() -> None:
    trajectory = make_demo_trajectory(length=conf.DEMO_TRAJECTORY_LENGTH)

    seed = (time.time_ns() % (2**32)) ^ (os.getpid() % (2**32))
    motive = trajectory_to_motive(
        trajectory,
        target_length=conf.MOTIVE_TARGET_LENGTH,
        base_duration=conf.MOTIVE_BASE_DURATION,
        seed=seed,
    )

    rng = random.Random(seed)
    transpose = rng.randint(conf.DEMO_TRANSPOSE_MIN, conf.DEMO_TRANSPOSE_MAX)
    bpm = rng.randint(conf.DEMO_BPM_MIN, conf.DEMO_BPM_MAX)
    motive = [
        Note(pitch=max(0, min(127, n.pitch + transpose)), duration=n.duration, velocity=n.velocity, start=n.start)
        for n in motive
    ]

    score = compose(motive, bpm=bpm, add_accompaniment=True)
    print("seed:", seed, "移调:", transpose, "半音 | BPM:", bpm, "| 轨迹:", len(trajectory), "→ 动机:", len(motive), "音", flush=True)
    play_score(score)


if __name__ == "__main__":
    main()
