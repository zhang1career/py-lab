"""
可调参数与写死常量集中配置（不含 0、1 等边界值）。
按功能分类，便于调参与维护。
"""

# -----------------------------------------------------------------------------
# 调性（动机与作曲）
# -----------------------------------------------------------------------------
KEY_ROOT_MIDI = 60
KEY_MODE = 'major'
COMPOSE_ARPEGGIO_NOTE_DURATION = 0.35
COMPOSE_COUNTERPOINT_VELOCITY_RATIO = 0.15
# -----------------------------------------------------------------------------
# 动机输出：音高与力度范围、默认长度与节奏
# -----------------------------------------------------------------------------
MOTIVE_ROOT_MIDI = 60
MOTIVE_PITCH_RANGE = 12
MOTIVE_TARGET_LENGTH = 16
MOTIVE_BASE_DURATION = 0.5
MOTIVE_MIN_VELOCITY = 0.95
MOTIVE_MAX_VELOCITY = 1.0
MOTIVE_STYLE = 'lyrical'
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
TRAJ_SHUFFLE_READ_ORDER = False
TRAJ_PITCH_NOISE_SEMITONES = 0
TRAJ_INVERSE_CDF_MID = 0.5
# -----------------------------------------------------------------------------
# 轨迹→动机：随机扰动（方向 / 速度 / 力度 / 轮廓）
# -----------------------------------------------------------------------------
TRAJ_AGGREGATE_DIR_NOISE = 1.8
TRAJ_AGGREGATE_VEL_NOISE = 0.55
TRAJ_AGGREGATE_INT_NOISE = 0.55
TRAJ_CONTOUR_RANDOM_SCALE = 3.0
TRAJ_CONTOUR_DIR_WEIGHT = 0.4
TRAJ_SINGLE_STEP_NOISE = 2.2
TRAJ_SINGLE_DIR_WEIGHT = 0.5
TRAJ_SINGLE_VEL_NOISE = 0.3
TRAJ_SINGLE_INT_NOISE = 0.5
TRAJ_VEL_TO_DUR_OFFSET = 2.0
# -----------------------------------------------------------------------------
# 作曲器：伴奏与和声
# -----------------------------------------------------------------------------
COMPOSE_DEFAULT_BPM = 120
COMPOSE_ADD_ACCOMPANIMENT = True
COMPOSE_ACCOMPANIMENT_VELOCITY = 0.25
COMPOSE_CHORD_DURATION = 4.0
COMPOSE_ACCOMPANIMENT_STYLE = 'rhythm_pattern'
COMPOSE_ADD_COUNTERPOINT = True
COMPOSE_COUNTERPOINT_STYLE = 'secondary_melody'
# -----------------------------------------------------------------------------
# 作曲器：叠加层（Pad / 低音 / 打击 / 装饰）
# -----------------------------------------------------------------------------
COMPOSE_ADD_PAD = True
COMPOSE_PAD_VELOCITY = 0.06
COMPOSE_PAD_CHORD_DURATION = 4.0
COMPOSE_PAD_OCTAVE_OFFSET = 1
COMPOSE_ADD_BASS = True
COMPOSE_BASS_VELOCITY = 0.05
COMPOSE_BASS_STYLE = 'root_fifth'
COMPOSE_BASS_OCTAVE_OFFSET = -1
COMPOSE_ADD_PERCUSSION = True
COMPOSE_PERCUSSION_VELOCITY = 0.1
COMPOSE_PERCUSSION_PATTERN = 'simple_44'
COMPOSE_PERCUSSION_PLAYBACK = 'gm'
COMPOSE_ADD_ORNAMENTATION = True
COMPOSE_ORNAMENT_VELOCITY_RATIO = 0.12
COMPOSE_ORNAMENT_DENSITY = 0.3
COMPOSE_ORNAMENT_MAX_DURATION = 0.25
TIME_SIGNATURE_NUMERATOR = 4
TIME_SIGNATURE_DENOMINATOR = 4
# -----------------------------------------------------------------------------
# 律动：4/4 强拍与摇摆
# -----------------------------------------------------------------------------
BEATS_PER_BAR = 4
GROOVE_ACCENT_STRONG_BEAT_FACTOR = 1.25
GROOVE_SWING_AMOUNT = 0.25
# -----------------------------------------------------------------------------
# 播放器：音频与包络
# -----------------------------------------------------------------------------
PLAYER_SAMPLE_RATE = 44100
PLAYER_A4_FREQ = 440.0
PLAYER_A4_MIDI = 70
PLAYER_FADE_DIVISOR = 32
PLAYER_FADE_MAX_SAMPLES = 256
PLAYER_MASTER_GAIN = 0.8
PLAYER_OVERTONE_2_RATIO = 0.5
PLAYER_OVERTONE_3_RATIO = 0.33
PLAYER_ATTACK_SEC = 0.01
PLAYER_DECAY_SEC = 0.05
PLAYER_SUSTAIN_LEVEL = 0.7
PLAYER_RELEASE_SEC = 0.05
PLAYER_REVERB_WET = 0.2
PLAYER_REVERB_LENGTH_SEC = 0.4
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
