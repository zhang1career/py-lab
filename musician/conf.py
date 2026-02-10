"""
可调参数与写死常量集中配置（不含 0、1 等边界值）。
按功能分类，便于调参与维护。
"""

# -----------------------------------------------------------------------------
# 动机输出：音高与力度范围、默认长度与节奏
# -----------------------------------------------------------------------------
MOTIVE_ROOT_MIDI = 60           # 动机基准音高 (C4)
MOTIVE_PITCH_RANGE = 12        # 音高相对基准的 ±半音范围
MOTIVE_TARGET_LENGTH = 64      # 固定输出动机长度（音符数）
MOTIVE_BASE_DURATION = 0.25    # 基准时值（拍），速度映射会在此基础上缩放
MOTIVE_MIN_VELOCITY = 0.3      # 力度下界 [0,1]
MOTIVE_MAX_VELOCITY = 0.95    # 力度上界 [0,1]

# -----------------------------------------------------------------------------
# 轨迹→动机：权重与 warp
# -----------------------------------------------------------------------------
# 轨迹每点权重：weight = intensity * (VELOCITY_OFFSET + velocity) + WEIGHT_FLOOR + DIR_CHANGE_WEIGHT * 方向变化
TRAJ_WEIGHT_VELOCITY_OFFSET = 0.5
TRAJ_WEIGHT_FLOOR = 0.1
TRAJ_WEIGHT_DIR_CHANGE = 0.3
# warp 幂次：alpha = WARP_ALPHA_LO + WARP_ALPHA_SPAN * mean_velocity
TRAJ_WARP_ALPHA_LO = 0.85
TRAJ_WARP_ALPHA_SPAN = 0.3
# 采样邻域半径 = trajectory_len // RADIUS_DIVISOR
TRAJ_RADIUS_DIVISOR = 16
# 位置抖动：jitter = trajectory_len * JITTER_SCALE_FACTOR
TRAJ_JITTER_SCALE_FACTOR = 0.08
# 打乱「输出音序号 ↔ 轨迹位置」的对应关系，使旋律由非线性映射得到（非按时间顺序采样）
TRAJ_SHUFFLE_READ_ORDER = True
# 每个音符在轮廓基础上再加的随机半音偏移 ±N，增强旋律随机性
TRAJ_PITCH_NOISE_SEMITONES = 3
# CDF 单点时的查询位置
TRAJ_INVERSE_CDF_MID = 0.5

# -----------------------------------------------------------------------------
# 轨迹→动机：随机扰动（方向 / 速度 / 力度 / 轮廓）
# -----------------------------------------------------------------------------
# 邻域聚合后的方向扰动幅度 (rng-0.5)*
TRAJ_AGGREGATE_DIR_NOISE = 1.8
# 邻域聚合后的速度、力度扰动幅度
TRAJ_AGGREGATE_VEL_NOISE = 0.55
TRAJ_AGGREGATE_INT_NOISE = 0.55
# 轮廓步长：step = (rng-0.5)*CONTOUR_RANDOM_SCALE + d*CONTOUR_DIR_WEIGHT（随机为主，轨迹为偏置）
TRAJ_CONTOUR_RANDOM_SCALE = 5.0
TRAJ_CONTOUR_DIR_WEIGHT = 0.4
# 单点轨迹随机游走：步长 (rng-0.5)*，方向偏置 d0*
TRAJ_SINGLE_STEP_NOISE = 2.2
TRAJ_SINGLE_DIR_WEIGHT = 0.5
TRAJ_SINGLE_VEL_NOISE = 0.5
TRAJ_SINGLE_INT_NOISE = 0.5
# 速度→时值：duration = base_duration * (VEL_TO_DUR_OFFSET - velocity)
TRAJ_VEL_TO_DUR_OFFSET = 1.5

# -----------------------------------------------------------------------------
# 作曲器：伴奏与和声
# -----------------------------------------------------------------------------
COMPOSE_DEFAULT_BPM = 120
COMPOSE_ACCOMPANIMENT_VELOCITY = 0.35
COMPOSE_CHORD_DURATION = 2.0   # 每和弦持续拍数
# C 大调 I-IV-V-I 块状和弦 (MIDI)
COMPOSE_CHORDS = [
    [60, 64, 67],   # C
    [65, 69, 72],   # F
    [67, 71, 74],   # G
    [60, 64, 67],   # C
]

# -----------------------------------------------------------------------------
# 播放器：音频与包络
# -----------------------------------------------------------------------------
PLAYER_SAMPLE_RATE = 44100
PLAYER_A4_FREQ = 440.0
PLAYER_A4_MIDI = 69
PLAYER_SEMITONE_RATIO = 12
PLAYER_FADE_DIVISOR = 32       # 淡入淡出长度 = min(dur_samples//this, FADE_MAX_SAMPLES)
PLAYER_FADE_MAX_SAMPLES = 256
PLAYER_MASTER_GAIN = 0.8      # 归一化后的整体增益
PLAYER_INT16_SCALE = 32767

# -----------------------------------------------------------------------------
# 演示 (__main__)：示例轨迹与随机范围
# -----------------------------------------------------------------------------
DEMO_TRAJECTORY_LENGTH = 64
DEMO_VELOCITY_LO = 0.3
DEMO_VELOCITY_HI_SPAN = 0.6    # velocity = LO + HI_SPAN * (1 - (t-0.5)^2)
DEMO_DIRECTION_SCALE = 0.8    # direction = 360 * t * this
DEMO_INTENSITY_LO = 0.4
DEMO_INTENSITY_HI_SPAN = 0.5
DEMO_INTENSITY_SIN_FREQ = 0.7
DEMO_TRANSPOSE_MIN = -12
DEMO_TRANSPOSE_MAX = 12
DEMO_BPM_MIN = 72
DEMO_BPM_MAX = 108
