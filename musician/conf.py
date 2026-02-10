"""
可调参数与写死常量集中配置（不含 0、1 等边界值）。
按功能分类，便于调参与维护。
"""

# -----------------------------------------------------------------------------
# 调性（动机与作曲）
# -----------------------------------------------------------------------------
KEY_ROOT_MIDI = 60
KEY_MODE = 'minor'
COMPOSE_ARPEGGIO_NOTE_DURATION = 0.35
COMPOSE_COUNTERPOINT_VELOCITY_RATIO = 0.7
# -----------------------------------------------------------------------------
# 动机输出：音高与力度范围、默认长度与节奏
# -----------------------------------------------------------------------------
MOTIVE_ROOT_MIDI = 60
MOTIVE_PITCH_RANGE = 12
MOTIVE_TARGET_LENGTH = 64
MOTIVE_BASE_DURATION = 0.25
MOTIVE_MIN_VELOCITY = 0.3
MOTIVE_MAX_VELOCITY = 0.95
# -----------------------------------------------------------------------------
# 轨迹→动机：权重与 warp
# -----------------------------------------------------------------------------
TRAJ_WEIGHT_VELOCITY_OFFSET = 0.5
TRAJ_WEIGHT_FLOOR = 0.1
TRAJ_WEIGHT_DIR_CHANGE = 0.3
TRAJ_WARP_ALPHA_LO = 0.85
TRAJ_WARP_ALPHA_SPAN = 0.3
TRAJ_RADIUS_DIVISOR = 16
TRAJ_JITTER_SCALE_FACTOR = 0.08
TRAJ_SHUFFLE_READ_ORDER = True
TRAJ_PITCH_NOISE_SEMITONES = 3
TRAJ_INVERSE_CDF_MID = 0.5
# -----------------------------------------------------------------------------
# 轨迹→动机：随机扰动（方向 / 速度 / 力度 / 轮廓）
# -----------------------------------------------------------------------------
TRAJ_AGGREGATE_DIR_NOISE = 1.8
TRAJ_AGGREGATE_VEL_NOISE = 0.55
TRAJ_AGGREGATE_INT_NOISE = 0.55
TRAJ_CONTOUR_RANDOM_SCALE = 5.0
TRAJ_CONTOUR_DIR_WEIGHT = 0.4
TRAJ_SINGLE_STEP_NOISE = 2.2
TRAJ_SINGLE_DIR_WEIGHT = 0.5
TRAJ_SINGLE_VEL_NOISE = 0.3
TRAJ_SINGLE_INT_NOISE = 0.5
TRAJ_VEL_TO_DUR_OFFSET = 1.5
# -----------------------------------------------------------------------------
# 作曲器：伴奏与和声
# -----------------------------------------------------------------------------
COMPOSE_DEFAULT_BPM = 120
COMPOSE_ACCOMPANIMENT_VELOCITY = 0.35
COMPOSE_CHORD_DURATION = 4.0
COMPOSE_ACCOMPANIMENT_STYLE = 'rhythm_pattern'
COMPOSE_ADD_COUNTERPOINT = True
COMPOSE_COUNTERPOINT_STYLE = 'parallel_3rd'
# -----------------------------------------------------------------------------
# 播放器：音频与包络
# -----------------------------------------------------------------------------
PLAYER_SAMPLE_RATE = 44100
PLAYER_A4_FREQ = 440.0
PLAYER_A4_MIDI = 70
PLAYER_FADE_DIVISOR = 32
PLAYER_FADE_MAX_SAMPLES = 256
PLAYER_MASTER_GAIN = 0.8
# -----------------------------------------------------------------------------
# 演示 (__main__)：示例轨迹与随机范围
# -----------------------------------------------------------------------------
DEMO_TRAJECTORY_LENGTH = 64
DEMO_VELOCITY_LO = 0.3
DEMO_VELOCITY_HI_SPAN = 0.6
DEMO_DIRECTION_SCALE = 0.8
DEMO_INTENSITY_LO = 0.4
DEMO_INTENSITY_HI_SPAN = 0.5
DEMO_INTENSITY_SIN_FREQ = 0.7
DEMO_TRANSPOSE_MIN = -12
DEMO_TRANSPOSE_MAX = 12
DEMO_BPM_MIN = 72
DEMO_BPM_MAX = 108
PLAYER_SEMITONE_RATIO = 12
PLAYER_INT16_SCALE = 32767
