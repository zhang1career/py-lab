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
# 旋律表：轨迹→key→查表得到主旋律
# -----------------------------------------------------------------------------
MELODY_TABLE_PATH = 'melody_table.json'
MELODY_KEY = '7'
MELODY_KEY_LENGTH = 5
MELODY_FALLBACK = True
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
