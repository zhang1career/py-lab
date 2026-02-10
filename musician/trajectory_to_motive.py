"""
将空间运动轨迹映射为音乐动机（旋律轮廓、节奏、力度）。

任意长度轨迹 → 固定长度动机。采用非线性、不可逆映射：
- 按轨迹「能量」分布做非等权 warp，而非按索引线性重采样；
- 每个输出音由轨迹上局部邻域聚合得到，并加入轻微随机扰动。
"""
import random
from typing import List, Optional, Tuple

from . import conf
from .models import TrajectoryPoint, Trajectory, Note, Motive


def trajectory_to_motive(
    trajectory: Trajectory,
    target_length: int = conf.MOTIVE_TARGET_LENGTH,
    root_midi: int = conf.MOTIVE_ROOT_MIDI,
    pitch_range: int = conf.MOTIVE_PITCH_RANGE,
    base_duration: float = conf.MOTIVE_BASE_DURATION,
    min_velocity: float = conf.MOTIVE_MIN_VELOCITY,
    max_velocity: float = conf.MOTIVE_MAX_VELOCITY,
    *,
    seed: Optional[int] = None,
) -> Motive:
    """
    将任意长度轨迹映射为固定长度动机（默认 64 个音）。

    映射为非线性、不可逆：
    - 按轨迹上的「能量」分布（力度×速度 + 方向变化）做 warp，使输出在能量空间近似等距；
    - 每个输出音由轨迹上一段邻域聚合得到，并加轻微随机扰动，无法从动机精确反推轨迹。
    """
    if not trajectory:
        return []

    rng = random.Random(seed)
    n = len(trajectory)
    if n == 1:
        # 单点：用该点特征生成 target_length 个音，用随机游走引入变化
        return _single_point_motive(
            trajectory[0], target_length, rng,
            root_midi, pitch_range, base_duration, min_velocity, max_velocity,
        )

    # 1) 轨迹上每点的「权重」：力度、速度、以及方向变化量（强调转折处）
    weights = _content_weights(trajectory)
    cdf = _weights_to_cdf(weights)

    # 2) 非线性的「输出索引 → 轨迹位置」：warp + 抖动后，再打乱「第 k 个音 ↔ 第几个轨迹位置」的对应
    warp_alpha = _warp_alpha(trajectory)
    trajectory_positions = _warp_to_positions(cdf, target_length, warp_alpha)
    trajectory_positions = _jitter_positions(trajectory_positions, n, rng)
    if conf.TRAJ_SHUFFLE_READ_ORDER:
        # 随机排列：旋律不再按轨迹时间顺序采样，同一轨迹每次得到完全不同的音高序列
        perm = list(range(target_length))
        rng.shuffle(perm)
        trajectory_positions = [trajectory_positions[j] for j in perm]

    # 3) 每个位置做邻域聚合 + 扰动，得到 target_length 组 (direction, velocity, intensity)
    dirs: List[float] = []
    vels: List[float] = []
    ints: List[float] = []
    radius = max(1, n // conf.TRAJ_RADIUS_DIVISOR)
    for pos in trajectory_positions:
        d, v, i = _aggregate_at_position(trajectory, pos, radius, rng)
        dirs.append(d)
        vels.append(v)
        ints.append(i)

    # 4) 由方向序列做随机主导的累积轮廓 → 音高偏移，再对每个音加独立随机半音偏移
    pitch_offsets = _contour_with_noise(dirs, pitch_range, rng)
    noise_range = conf.TRAJ_PITCH_NOISE_SEMITONES
    for k in range(target_length):
        pitch_offsets[k] += rng.randint(-noise_range, noise_range)

    # 5) 组装固定长度的动机
    motive: List[Note] = []
    t = 0.0
    for k in range(target_length):
        dur = _velocity_to_duration(vels[k], base_duration)
        vel = min_velocity + ints[k] * (max_velocity - min_velocity)
        vel = max(0.0, min(1.0, vel))
        pitch = int(max(0, min(127, root_midi + pitch_offsets[k])))
        motive.append(Note(pitch=pitch, duration=dur, velocity=vel, start=t))
        t += dur
    return motive


def _content_weights(trajectory: Trajectory) -> List[float]:
    """每点的权重：力度×(0.5+速度) + 方向变化量，避免为 0。"""
    weights = []
    prev_dir = _normalize_direction(trajectory[0].direction)
    for i, p in enumerate(trajectory):
        d = _normalize_direction(p.direction)
        change = abs(d - prev_dir) if i > 0 else 0
        prev_dir = d
        w = p.intensity * (conf.TRAJ_WEIGHT_VELOCITY_OFFSET + max(0.0, min(1.0, p.velocity))) + conf.TRAJ_WEIGHT_FLOOR + conf.TRAJ_WEIGHT_DIR_CHANGE * change
        weights.append(w)
    return weights


def _weights_to_cdf(weights: List[float]) -> List[float]:
    """权重序列转为 CDF（首为 0，末为 1）。"""
    total = sum(weights)
    if total <= 0:
        return [i / max(1, len(weights) - 1) for i in range(len(weights))]
    cdf = [0.0]
    for w in weights:
        cdf.append(cdf[-1] + w / total)
    return cdf


def _warp_alpha(trajectory: Trajectory) -> float:
    """由轨迹整体特征决定 warp 的幂次，使映射与轨迹内容相关。"""
    mean_vel = sum(p.velocity for p in trajectory) / len(trajectory)
    mean_vel = max(0.0, min(1.0, mean_vel))
    # 速度偏大时 alpha 略 >1，使时间轴前段更密；否则略 <1
    return conf.TRAJ_WARP_ALPHA_LO + conf.TRAJ_WARP_ALPHA_SPAN * mean_vel


def _jitter_positions(positions: List[float], trajectory_len: int, rng: random.Random) -> List[float]:
    """对每个采样位置加随机偏移，使同一轨迹每次得到的旋律轮廓不同。"""
    jitter_scale = max(1.0, trajectory_len * conf.TRAJ_JITTER_SCALE_FACTOR)
    return [
        max(0.0, min(float(trajectory_len - 1), pos + (rng.random() - 0.5) * jitter_scale))
        for pos in positions
    ]


def _warp_to_positions(cdf: List[float], target_length: int, alpha: float) -> List[float]:
    """
    得到 target_length 个轨迹位置（浮点索引）。
    在 CDF 空间等距取点，再经幂次 alpha 扭曲，使分布非线性。
    """
    if target_length <= 0:
        return []
    if target_length == 1:
        # 取 CDF 中点对应的索引
        return [_inverse_cdf(cdf, conf.TRAJ_INVERSE_CDF_MID)]
    positions = []
    for k in range(target_length):
        # 在 [0,1] 上等距
        u = k / (target_length - 1)
        # 非线性扭曲：u^alpha 或 1-(1-u)^alpha，使与 alpha 相关
        t = u ** alpha
        pos = _inverse_cdf(cdf, t)
        positions.append(pos)
    return positions


def _inverse_cdf(cdf: List[float], t: float) -> float:
    """CDF 值为 t 时对应的浮点索引（线性插值）。"""
    t = max(0.0, min(1.0, t))
    n = len(cdf) - 1
    if n <= 0:
        return 0.0
    for i in range(n):
        if cdf[i] <= t <= cdf[i + 1]:
            if cdf[i + 1] == cdf[i]:
                return float(i)
            frac = (t - cdf[i]) / (cdf[i + 1] - cdf[i])
            return float(i) + frac
    return float(n)


def _aggregate_at_position(
    trajectory: Trajectory,
    pos: float,
    radius: int,
    rng: random.Random,
) -> Tuple[float, float, float]:
    """在轨迹位置 pos 邻域内做加权聚合，并加轻微随机扰动。返回 (direction_norm, velocity, intensity)。"""
    n = len(trajectory)
    idx_lo = max(0, int(pos) - radius)
    idx_hi = min(n - 1, int(pos) + radius)
    # 高斯式权重：越靠近 pos 权重越大
    sum_d, sum_v, sum_i, sum_w = 0.0, 0.0, 0.0, 0.0
    for i in range(idx_lo, idx_hi + 1):
        dist = abs(i - pos)
        w = max(0.0, 1 - dist / (radius + 1))
        p = trajectory[i]
        sum_d += _normalize_direction(p.direction) * w
        sum_v += max(0.0, min(1.0, p.velocity)) * w
        sum_i += max(0.0, min(1.0, p.intensity)) * w
        sum_w += w
    if sum_w <= 0:
        p = trajectory[min(int(pos), n - 1)]
        d = _normalize_direction(p.direction)
        v = max(0.0, min(1.0, p.velocity))
        i = max(0.0, min(1.0, p.intensity))
        return d, v, i
    d = sum_d / sum_w
    v = sum_v / sum_w
    i = sum_i / sum_w
    # 不可逆：加较大随机扰动，使每次运行听感明显不同
    d = d + (rng.random() - 0.5) * conf.TRAJ_AGGREGATE_DIR_NOISE
    v = max(0.0, min(1.0, v + (rng.random() - 0.5) * conf.TRAJ_AGGREGATE_VEL_NOISE))
    i = max(0.0, min(1.0, i + (rng.random() - 0.5) * conf.TRAJ_AGGREGATE_INT_NOISE))
    return d, v, i


def _contour_with_noise(normalized_dirs: List[float], pitch_range: int, rng: random.Random) -> List[int]:
    """由方向序列做累积轮廓得到半音偏移；随机步长占主导，使每次旋律走向明显不同。"""
    offsets = []
    cum = 0.0
    for d in normalized_dirs:
        # 随机步长为主(±2)，轨迹方向为轻微偏置，这样音高轮廓每次都会变
        step = (rng.random() - 0.5) * conf.TRAJ_CONTOUR_RANDOM_SCALE + d * conf.TRAJ_CONTOUR_DIR_WEIGHT
        cum += step
        cum = max(-pitch_range, min(pitch_range, cum))
        offsets.append(int(round(cum)))
    return offsets


def _single_point_motive(
    point: TrajectoryPoint,
    target_length: int,
    rng: random.Random,
    root_midi: int,
    pitch_range: int,
    base_duration: float,
    min_velocity: float,
    max_velocity: float,
) -> Motive:
    """轨迹只有一个点时：用该点特征加随机游走生成 target_length 个音。"""
    d0 = _normalize_direction(point.direction)
    v0 = max(0.0, min(1.0, point.velocity))
    i0 = max(0.0, min(1.0, point.intensity))
    cum = 0.0
    motive: List[Note] = []
    t = 0.0
    for _ in range(target_length):
        cum += d0 * conf.TRAJ_SINGLE_DIR_WEIGHT + (rng.random() - 0.5) * conf.TRAJ_SINGLE_STEP_NOISE
        cum = max(-pitch_range, min(pitch_range, cum))
        v = max(0.0, min(1.0, v0 + (rng.random() - 0.5) * conf.TRAJ_SINGLE_VEL_NOISE))
        i = max(0.0, min(1.0, i0 + (rng.random() - 0.5) * conf.TRAJ_SINGLE_INT_NOISE))
        dur = _velocity_to_duration(v, base_duration)
        vel = min_velocity + i * (max_velocity - min_velocity)
        vel = max(0.0, min(1.0, vel))
        pitch = int(max(0, min(127, root_midi + round(cum))))
        motive.append(Note(pitch=pitch, duration=dur, velocity=vel, start=t))
        t += dur
    return motive


def _normalize_direction(d: float) -> float:
    """将方向归一化到 [-1, 1]。若 d 为角度 0~360，则映射为 -1~1。"""
    while d > 360:
        d -= 360
    while d < 0:
        d += 360
    return (d / 360.0) * 2 - 1


def _velocity_to_duration(velocity: float, base_duration: float) -> float:
    """速度大 → 时值短；速度小 → 时值长。"""
    v = max(0.0, min(1.0, velocity))
    return base_duration * (conf.TRAJ_VEL_TO_DUR_OFFSET - v)
