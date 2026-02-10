"""
最小应用：从示例轨迹生成动机 → 作曲 → 播放。
运行 main() 时打开控制面板，可调 conf 全部参数，通过开关键生成并播放。
播放在独立子进程中执行，避免音频库影响 Tk，确保播放结束后控制面板保持打开。
面板参数在防抖 80ms 后写回 conf.py；监控 musician 目录下 .py 文件（除 conf.py）变更并自动重启。
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional

from musician import conf

# 防抖延迟（ms）：面板修改后多久写回 conf.py；此时间内多次修改只触发一次保存
CONF_PY_DEBOUNCE_MS = 80
# 监控 musician 目录下 .py 文件的轮询间隔（秒）
WATCH_POLL_INTERVAL = 1.0
from musician.models import TrajectoryPoint, Note
from musician.trajectory_to_motive import trajectory_to_motive
from musician.composer import compose
from musician.export_midi import export_score_to_midi
from musician.export_ts_lib import export_ts_lib


# -----------------------------------------------------------------------------
# 控制面板：conf 参数分组与控件规格（名称、说明、类型、范围）
# -----------------------------------------------------------------------------
PANEL_GROUPS = [
    (
        "调性（动机与作曲）",
        [
            ("KEY_ROOT_MIDI", "int", 60, "调性根音 MIDI，如 60=C", 0, 127),
            ("KEY_MODE", "choice", "major", "大调/小调", "major", "minor"),
            ("COMPOSE_ARPEGGIO_NOTE_DURATION", "float", 0.25, "分解和弦每音时值（拍）", 0.125, 1.0),
            ("COMPOSE_COUNTERPOINT_VELOCITY_RATIO", "float", 0.7, "对位力度比例 [0,1]", 0.0, 1.0),
        ],
    ),
    (
        "动机输出（音高 / 力度 / 长度 / 节奏）",
        [
            ("MOTIVE_ROOT_MIDI", "int", 60, "基准音高 MIDI，如 60=C4", 0, 127),
            ("MOTIVE_PITCH_RANGE", "int", 12, "音高相对基准的 ±半音范围", 1, 24),
            ("MOTIVE_TARGET_LENGTH", "int", 64, "固定输出动机长度（音符数）", 8, 256),
            ("MOTIVE_BASE_DURATION", "float", 0.25, "基准时值（拍）", 0.05, 2.0),
            ("MOTIVE_MIN_VELOCITY", "float", 0.3, "力度下界 [0,1]", 0.0, 1.0),
            ("MOTIVE_MAX_VELOCITY", "float", 0.95, "力度上界 [0,1]", 0.0, 1.0),
            ("MOTIVE_STYLE", "choice", "default", "轨迹→动机风格", "default", "lyrical", "minimal"),
        ],
    ),
    (
        "轨迹→动机：权重与 warp",
        [
            ("TRAJ_WEIGHT_VELOCITY_OFFSET", "float", 0.5, "权重中速度项偏移", 0.0, 2.0),
            ("TRAJ_WEIGHT_FLOOR", "float", 0.1, "权重下限，避免为 0", 0.0, 1.0),
            ("TRAJ_WEIGHT_DIR_CHANGE", "float", 0.3, "方向变化在权重中的系数", 0.0, 2.0),
            ("TRAJ_WARP_ALPHA_LO", "float", 0.85, "warp 幂次下界", 0.3, 1.5),
            ("TRAJ_WARP_ALPHA_SPAN", "float", 0.3, "warp 幂次随速度的跨度", 0.0, 1.0),
            ("TRAJ_RADIUS_DIVISOR", "int", 16, "邻域半径 = 轨迹长 // 此值", 4, 64),
            ("TRAJ_JITTER_SCALE_FACTOR", "float", 0.08, "位置抖动相对轨迹长的比例", 0.0, 0.5),
            ("TRAJ_SHUFFLE_READ_ORDER", "bool", True, "打乱「音序↔轨迹位置」对应，旋律非线性"),
            ("TRAJ_PITCH_NOISE_SEMITONES", "int", 3, "每音随机半音偏移 ±N", 0, 12),
            ("TRAJ_INVERSE_CDF_MID", "float", 0.5, "单点轨迹时 CDF 查询位置", 0.0, 1.0),
        ],
    ),
    (
        "轨迹→动机：随机扰动",
        [
            ("TRAJ_AGGREGATE_DIR_NOISE", "float", 1.8, "邻域聚合方向扰动幅度", 0.0, 4.0),
            ("TRAJ_AGGREGATE_VEL_NOISE", "float", 0.55, "邻域聚合速度扰动幅度", 0.0, 2.0),
            ("TRAJ_AGGREGATE_INT_NOISE", "float", 0.55, "邻域聚合力度扰动幅度", 0.0, 2.0),
            ("TRAJ_CONTOUR_RANDOM_SCALE", "float", 5.0, "轮廓步长随机部分幅度", 0.0, 10.0),
            ("TRAJ_CONTOUR_DIR_WEIGHT", "float", 0.4, "轮廓步长中轨迹方向权重", 0.0, 2.0),
            ("TRAJ_SINGLE_STEP_NOISE", "float", 2.2, "单点轨迹随机游走步长噪声", 0.0, 5.0),
            ("TRAJ_SINGLE_DIR_WEIGHT", "float", 0.5, "单点轨迹方向偏置权重", 0.0, 2.0),
            ("TRAJ_SINGLE_VEL_NOISE", "float", 0.5, "单点轨迹速度扰动", 0.0, 2.0),
            ("TRAJ_SINGLE_INT_NOISE", "float", 0.5, "单点轨迹力度扰动", 0.0, 2.0),
            ("TRAJ_VEL_TO_DUR_OFFSET", "float", 1.5, "速度→时值公式中的偏移", 0.5, 3.0),
        ],
    ),
    (
        "作曲器",
        [
            ("COMPOSE_DEFAULT_BPM", "int", 120, "默认 BPM", 40, 240),
            ("COMPOSE_ADD_ACCOMPANIMENT", "bool", True, "添加伴奏声部"),
            ("COMPOSE_ACCOMPANIMENT_VELOCITY", "float", 0.35, "伴奏力度 [0,1]", 0.0, 1.0),
            ("COMPOSE_CHORD_DURATION", "float", 2.0, "每个和弦持续拍数", 0.5, 4.0),
            ("COMPOSE_ACCOMPANIMENT_STYLE", "choice", "block", "伴奏形态", "block", "arpeggiated", "rhythm_pattern"),
            ("COMPOSE_ADD_COUNTERPOINT", "bool", False, "添加对位/副旋律声部"),
            ("COMPOSE_COUNTERPOINT_STYLE", "choice", "parallel_3rd", "对位/副旋律风格", "parallel_3rd", "parallel_6th", "ostinato", "secondary_melody"),
        ],
    ),
    (
        "叠加层（Pad / 低音 / 打击 / 装饰）",
        [
            ("COMPOSE_ADD_PAD", "bool", False, "添加 Pad 铺底"),
            ("COMPOSE_PAD_VELOCITY", "float", 0.25, "Pad 力度 [0,1]", 0.0, 1.0),
            ("COMPOSE_PAD_CHORD_DURATION", "float", 4.0, "Pad 每和弦持续拍数", 1.0, 8.0),
            ("COMPOSE_PAD_OCTAVE_OFFSET", "int", 1, "Pad 音区（相对根音八度）", -1, 3),
            ("COMPOSE_ADD_BASS", "bool", False, "添加低音线"),
            ("COMPOSE_BASS_VELOCITY", "float", 0.4, "低音力度 [0,1]", 0.0, 1.0),
            ("COMPOSE_BASS_STYLE", "choice", "root_only", "低音形态", "root_only", "root_fifth"),
            ("COMPOSE_BASS_OCTAVE_OFFSET", "int", -1, "低音音区（相对根音八度）", -3, 0),
            ("COMPOSE_ADD_PERCUSSION", "bool", False, "添加打击轨"),
            ("COMPOSE_PERCUSSION_VELOCITY", "float", 0.5, "打击力度 [0,1]", 0.0, 1.0),
            ("COMPOSE_PERCUSSION_PATTERN", "choice", "simple_44", "打击节奏型", "simple_44"),
            ("COMPOSE_PERCUSSION_PLAYBACK", "choice", "gm", "打击播放", "gm", "c2"),
            ("COMPOSE_ADD_ORNAMENTATION", "bool", False, "添加装饰音"),
            ("COMPOSE_ORNAMENT_VELOCITY_RATIO", "float", 0.6, "装饰力度比例 [0,1]", 0.0, 1.0),
            ("COMPOSE_ORNAMENT_DENSITY", "float", 0.3, "装饰密度 [0,1]", 0.0, 1.0),
            ("COMPOSE_ORNAMENT_MAX_DURATION", "float", 0.25, "装饰音最大时值（拍）", 0.125, 0.5),
        ],
    ),
    (
        "律动（4/4 强拍与摇摆）",
        [
            ("BEATS_PER_BAR", "int", 4, "每小节拍数（仅支持 4）", 4, 4),
            ("GROOVE_ACCENT_STRONG_BEAT_FACTOR", "float", 1.25, "强拍力度倍数", 1.0, 2.0),
            ("GROOVE_SWING_AMOUNT", "float", 0.25, "八分摇摆量（后半八分延后）", 0.0, 0.5),
        ],
    ),
    (
        "播放器",
        [
            ("PLAYER_SAMPLE_RATE", "int", 44100, "采样率 Hz", 8000, 96000),
            ("PLAYER_A4_FREQ", "float", 440.0, "A4 标准频率 Hz", 400.0, 480.0),
            ("PLAYER_A4_MIDI", "int", 69, "A4 的 MIDI 音高", 60, 72),
            ("PLAYER_FADE_DIVISOR", "int", 32, "淡入淡出长度除数", 8, 128),
            ("PLAYER_FADE_MAX_SAMPLES", "int", 256, "淡入淡出最大采样数", 64, 1024),
            ("PLAYER_MASTER_GAIN", "float", 0.8, "总增益 [0,1]", 0.1, 1.0),
            ("PLAYER_OVERTONE_2_RATIO", "float", 0.5, "二次泛音比例", 0.0, 1.0),
            ("PLAYER_OVERTONE_3_RATIO", "float", 0.33, "三次泛音比例", 0.0, 1.0),
            ("PLAYER_ATTACK_SEC", "float", 0.01, "ADSR 起音（秒）", 0.0, 0.1),
            ("PLAYER_DECAY_SEC", "float", 0.05, "ADSR 衰减（秒）", 0.0, 0.2),
            ("PLAYER_SUSTAIN_LEVEL", "float", 0.7, "ADSR 持续电平 [0,1]", 0.0, 1.0),
            ("PLAYER_RELEASE_SEC", "float", 0.05, "ADSR 释音（秒）", 0.0, 0.3),
            ("PLAYER_REVERB_WET", "float", 0.2, "混响湿声比例 [0,1]", 0.0, 1.0),
            ("PLAYER_REVERB_LENGTH_SEC", "float", 0.4, "混响 IR 长度（秒）", 0.1, 1.0),
        ],
    ),
    (
        "演示（示例轨迹与随机范围）",
        [
            ("DEMO_TRAJECTORY_LENGTH", "int", 64, "示例轨迹点数", 8, 256),
            ("DEMO_VELOCITY_LO", "float", 0.3, "示例速度下界", 0.0, 1.0),
            ("DEMO_VELOCITY_HI_SPAN", "float", 0.6, "示例速度变化幅度", 0.0, 1.0),
            ("DEMO_DIRECTION_SCALE", "float", 0.8, "示例方向缩放", 0.0, 2.0),
            ("DEMO_INTENSITY_LO", "float", 0.4, "示例力度下界", 0.0, 1.0),
            ("DEMO_INTENSITY_HI_SPAN", "float", 0.5, "示例力度变化幅度", 0.0, 1.0),
            ("DEMO_INTENSITY_SIN_FREQ", "float", 0.7, "示例力度正弦频率", 0.1, 2.0),
            ("DEMO_TRANSPOSE_MIN", "int", -12, "随机移调下界（半音）", -24, 0),
            ("DEMO_TRANSPOSE_MAX", "int", 12, "随机移调上界（半音）", 0, 24),
            ("DEMO_BPM_MIN", "int", 72, "随机 BPM 下界", 40, 120),
            ("DEMO_BPM_MAX", "int", 108, "随机 BPM 上界", 60, 180),
        ],
    ),
]

# 面板中所有 conf 键名（用于导出到子进程）
_CONF_KEYS = [key for _title, params in PANEL_GROUPS for key, *_ in params]

# 两列布局：左列组数（按音乐理论：左=素材/动机，右=编曲/播放/演示）
# 左列：调性、动机输出、轨迹→动机(权重)、轨迹→动机(扰动)；右列：作曲器、播放器、演示
_PANEL_LEFT_COLUMN_GROUPS = 4

# 伴奏开关关闭时，以下参数控件应设为不可编辑
ACCOMPANIMENT_PARAM_KEYS = frozenset({
    "COMPOSE_ACCOMPANIMENT_VELOCITY",
    "COMPOSE_CHORD_DURATION",
    "COMPOSE_ACCOMPANIMENT_STYLE",
})
# 对位开关关闭时，以下参数控件应设为不可编辑
COUNTERPOINT_PARAM_KEYS = frozenset({
    "COMPOSE_COUNTERPOINT_VELOCITY_RATIO",
    "COMPOSE_COUNTERPOINT_STYLE",
})
PAD_PARAM_KEYS = frozenset({
    "COMPOSE_PAD_VELOCITY",
    "COMPOSE_PAD_CHORD_DURATION",
    "COMPOSE_PAD_OCTAVE_OFFSET",
})
BASS_PARAM_KEYS = frozenset({
    "COMPOSE_BASS_VELOCITY",
    "COMPOSE_BASS_STYLE",
    "COMPOSE_BASS_OCTAVE_OFFSET",
})
PERCUSSION_PARAM_KEYS = frozenset({
    "COMPOSE_PERCUSSION_VELOCITY",
    "COMPOSE_PERCUSSION_PATTERN",
    "COMPOSE_PERCUSSION_PLAYBACK",
})
ORNAMENT_PARAM_KEYS = frozenset({
    "COMPOSE_ORNAMENT_VELOCITY_RATIO",
    "COMPOSE_ORNAMENT_DENSITY",
    "COMPOSE_ORNAMENT_MAX_DURATION",
})


def _get_panel_values(vars_map: dict, kinds: dict) -> dict:
    """从面板变量得到键→值的字典（与 _apply_panel_to_conf 同一套转换）。"""
    out = {}
    for key, var in vars_map.items():
        kind = kinds.get(key, "float")
        val = var.get()
        if kind == "bool":
            out[key] = bool(val)
        elif kind == "int":
            try:
                out[key] = int(float(val))
            except (ValueError, TypeError):
                out[key] = getattr(conf, key, 0)
        elif kind == "choice":
            out[key] = str(val) if val else getattr(conf, key, "")
        else:
            try:
                out[key] = float(val)
            except (ValueError, TypeError):
                out[key] = getattr(conf, key, 0.0)
    return out


def _apply_panel_to_conf(vars_map: dict, kinds: dict) -> None:
    """将面板上的变量写回 conf 模块。kinds: key -> 'int'|'float'|'bool'。"""
    for key, value in _get_panel_values(vars_map, kinds).items():
        setattr(conf, key, value)


def _conf_py_key_order() -> list:
    """conf.py 中键的写出顺序（与 PANEL_GROUPS 一致，并补全非面板键）。"""
    keys = [key for _t, params in PANEL_GROUPS for key, *_ in params]
    # 律动小节中保留拍号（仅 4/4，不暴露在面板）
    for k in ("TIME_SIGNATURE_NUMERATOR", "TIME_SIGNATURE_DENOMINATOR"):
        if k not in keys:
            idx = keys.index("BEATS_PER_BAR") if "BEATS_PER_BAR" in keys else len(keys)
            keys.insert(idx, k)
    for k in ("PLAYER_SEMITONE_RATIO", "PLAYER_INT16_SCALE"):
        if k not in keys:
            keys.append(k)
    return keys


def _conf_py_section_for_key(key: str) -> Optional[str]:
    """返回该键所属的 conf.py 小节标题（仅在该节第一个键时返回，用于插入注释）。"""
    if key == "KEY_ROOT_MIDI":
        return "# 调性（动机与作曲）"
    if key == "MOTIVE_ROOT_MIDI":
        return "# 动机输出：音高与力度范围、默认长度与节奏"
    if key == "TRAJ_WEIGHT_VELOCITY_OFFSET":
        return "# 轨迹→动机：权重与 warp"
    if key == "TRAJ_AGGREGATE_DIR_NOISE":
        return "# 轨迹→动机：随机扰动（方向 / 速度 / 力度 / 轮廓）"
    if key == "COMPOSE_DEFAULT_BPM":
        return "# 作曲器：伴奏与和声"
    if key == "COMPOSE_ADD_PAD":
        return "# 作曲器：叠加层（Pad / 低音 / 打击 / 装饰）"
    if key == "BEATS_PER_BAR":
        return "# 律动：4/4 强拍与摇摆"
    if key == "PLAYER_SAMPLE_RATE":
        return "# 播放器：音频与包络"
    if key == "DEMO_TRAJECTORY_LENGTH":
        return "# 演示 (__main__)：示例轨迹与随机范围"
    return None


def _format_conf_value(key: str, value) -> str:
    """将单个 conf 值格式化为 Python 源码形式。"""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        return repr(value)
    return repr(value)


def _write_conf_py_file(path: str, vars_map: dict, kinds: dict) -> None:
    """将面板参数及 conf 中非面板键写入 conf.py 文件。"""
    values = _get_panel_values(vars_map, kinds)
    for k in _conf_py_key_order():
        if k not in values and hasattr(conf, k):
            values[k] = getattr(conf, k)
    lines = [
        '"""',
        "可调参数与写死常量集中配置（不含 0、1 等边界值）。",
        "按功能分类，便于调参与维护。",
        '"""',
        "",
    ]
    last_section: Optional[str] = None
    for key in _conf_py_key_order():
        if key not in values:
            continue
        section = _conf_py_section_for_key(key)
        if section and section != last_section:
            lines.append("# -----------------------------------------------------------------------------")
            lines.append(section)
            lines.append("# -----------------------------------------------------------------------------")
            last_section = section
        val = values[key]
        lines.append(f"{key} = {_format_conf_value(key, val)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _save_conf_to_file(path: str) -> None:
    """将当前 conf 中面板涉及的键写入 JSON 文件，供子进程加载。"""
    data = {}
    for k in _CONF_KEYS:
        v = getattr(conf, k, None)
        if isinstance(v, bool):
            data[k] = v
        elif isinstance(v, (int, float)):
            data[k] = v
        else:
            data[k] = v
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=0)


def _run_playback_in_subprocess(conf_path: str, cwd: str) -> int:
    """在子进程中加载 conf 并执行生成+播放，返回子进程退出码。不导入 Tk。"""
    script = r"""
import json
import os
import random
import time
from musician import conf
from musician.models import TrajectoryPoint, Note
from musician.trajectory_to_motive import trajectory_to_motive
from musician.composer import compose
from musician.player import play_score

path = os.environ.get("MUSICIAN_CONF_FILE")
if path and os.path.isfile(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for k, v in data.items():
        setattr(conf, k, v)

def make_trajectory(length):
    import math
    points = []
    n = length - 1
    for i in range(length):
        t = i / n if n > 0 else 1
        velocity = conf.DEMO_VELOCITY_LO + conf.DEMO_VELOCITY_HI_SPAN * (1 - (t - 0.5) ** 2)
        direction = 360 * t * conf.DEMO_DIRECTION_SCALE
        intensity = conf.DEMO_INTENSITY_LO + conf.DEMO_INTENSITY_HI_SPAN * (0.5 + 0.5 * math.sin(i * conf.DEMO_INTENSITY_SIN_FREQ))
        points.append(TrajectoryPoint(velocity=velocity, direction=direction, intensity=min(1.0, intensity)))
    return points

trajectory = make_trajectory(conf.DEMO_TRAJECTORY_LENGTH)
seed = (time.time_ns() % (2**32)) ^ (os.getpid() % (2**32))
motive = trajectory_to_motive(
    trajectory,
    target_length=conf.MOTIVE_TARGET_LENGTH,
    base_duration=conf.MOTIVE_BASE_DURATION,
    key_root_midi=getattr(conf, "KEY_ROOT_MIDI", 60),
    key_mode=getattr(conf, "KEY_MODE", "major"),
    seed=seed,
    style=getattr(conf, "MOTIVE_STYLE", "default"),
)
rng = random.Random(seed)
transpose = rng.randint(conf.DEMO_TRANSPOSE_MIN, conf.DEMO_TRANSPOSE_MAX)
bpm = rng.randint(conf.DEMO_BPM_MIN, conf.DEMO_BPM_MAX)
motive = [Note(pitch=max(0, min(127, n.pitch + transpose)), duration=n.duration, velocity=n.velocity, start=n.start) for n in motive]
score = compose(
    motive,
    bpm=bpm,
    add_accompaniment=getattr(conf, "COMPOSE_ADD_ACCOMPANIMENT", True),
    accompaniment_velocity=getattr(conf, "COMPOSE_ACCOMPANIMENT_VELOCITY", 0.35),
    accompaniment_style=getattr(conf, "COMPOSE_ACCOMPANIMENT_STYLE", "block"),
    add_counterpoint=getattr(conf, "COMPOSE_ADD_COUNTERPOINT", False),
    counterpoint_style=getattr(conf, "COMPOSE_COUNTERPOINT_STYLE", "parallel_3rd"),
    add_pad=getattr(conf, "COMPOSE_ADD_PAD", False),
    pad_velocity=getattr(conf, "COMPOSE_PAD_VELOCITY", 0.25),
    pad_chord_duration=getattr(conf, "COMPOSE_PAD_CHORD_DURATION", 4.0),
    pad_octave_offset=getattr(conf, "COMPOSE_PAD_OCTAVE_OFFSET", 1),
    add_bass=getattr(conf, "COMPOSE_ADD_BASS", False),
    bass_velocity=getattr(conf, "COMPOSE_BASS_VELOCITY", 0.4),
    bass_style=getattr(conf, "COMPOSE_BASS_STYLE", "root_only"),
    bass_octave_offset=getattr(conf, "COMPOSE_BASS_OCTAVE_OFFSET", -1),
    add_percussion=getattr(conf, "COMPOSE_ADD_PERCUSSION", False),
    percussion_velocity=getattr(conf, "COMPOSE_PERCUSSION_VELOCITY", 0.5),
    percussion_pattern=getattr(conf, "COMPOSE_PERCUSSION_PATTERN", "simple_44"),
    add_ornamentation=getattr(conf, "COMPOSE_ADD_ORNAMENTATION", False),
    ornament_velocity_ratio=getattr(conf, "COMPOSE_ORNAMENT_VELOCITY_RATIO", 0.6),
    ornament_density=getattr(conf, "COMPOSE_ORNAMENT_DENSITY", 0.3),
    ornament_max_duration=getattr(conf, "COMPOSE_ORNAMENT_MAX_DURATION", 0.25),
    key_root_midi=getattr(conf, "KEY_ROOT_MIDI", 60),
    key_mode=getattr(conf, "KEY_MODE", "major"),
)
play_score(score)
"""
    env = {**os.environ, "MUSICIAN_CONF_FILE": conf_path}
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=cwd,
        env=env,
    )
    return result.returncode


def _generate_and_play(root: tk.Tk, status_var: tk.StringVar) -> None:
    """在后台线程中：写 conf 到临时文件，启动子进程执行生成+播放；子进程结束后仅更新状态，不触碰 Tk。"""
    def set_status(msg: str) -> None:
        root.after(0, lambda m=msg: status_var.set(m))

    try:
        set_status("生成并播放中…")
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            _save_conf_to_file(path)
            cwd = os.getcwd()
            code = _run_playback_in_subprocess(path, cwd)
            if code == 0:
                set_status("播放完成，可继续调参并再次点击「生成并播放」")
            else:
                set_status(f"子进程退出码: {code}")
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    except Exception as e:
        set_status(f"错误: {e}")


def make_demo_trajectory(length: int) -> list[TrajectoryPoint]:
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


def _build_group(
    parent: tk.Widget,
    title: str,
    params: list,
    vars_map: dict,
    kinds: dict,
    dependent_widgets: Optional[dict] = None,
) -> None:
    """在 parent 下建一个分组（LabelFrame）及参数控件。
    dependent_widgets: 若提供，则对伴奏/对位相关 key 记录其可编辑控件，用于随开关启用/禁用。
    """
    frame = ttk.LabelFrame(parent, text=title, padding=6)
    frame.pack(fill=tk.X, padx=4, pady=4)
    if dependent_widgets is None:
        dependent_widgets = {}
    for key, kind, default, hint, *rest in params:
        kinds[key] = kind
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=key, width=32, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 4))
        row_widgets: list = []
        if kind == "bool":
            var = tk.BooleanVar(value=getattr(conf, key, default))
            cb = ttk.Checkbutton(row, variable=var, text="开启")
            cb.pack(side=tk.LEFT)
            vars_map[key] = var
        elif kind == "choice":
            options = list(rest)
            current = getattr(conf, key, default)
            if current not in options and options:
                current = options[0]
            var = tk.StringVar(value=current)
            # 用单选按钮替代下拉框，避免 macOS 上 OptionMenu/Combobox 选中后不显示文字的问题
            for opt in options:
                rb = ttk.Radiobutton(row, variable=var, value=opt, text=opt)
                rb.pack(side=tk.LEFT, padx=(0, 8))
                row_widgets.append(rb)
            vars_map[key] = var
        elif kind == "int":
            lo, hi = rest[0], rest[1]
            var = tk.StringVar(value=str(getattr(conf, key, default)))
            sb = ttk.Spinbox(row, from_=lo, to=hi, width=8, textvariable=var)
            sb.pack(side=tk.LEFT)
            vars_map[key] = var
            row_widgets.append(sb)
        else:
            lo, hi = rest[0], rest[1]
            var = tk.StringVar(value=str(getattr(conf, key, default)))
            sb = ttk.Spinbox(row, from_=lo, to=hi, width=8, textvariable=var, increment=0.05 if (hi - lo) <= 2 else 1.0)
            sb.pack(side=tk.LEFT)
            vars_map[key] = var
            row_widgets.append(sb)
        if row_widgets and (
            key in ACCOMPANIMENT_PARAM_KEYS
            or key in COUNTERPOINT_PARAM_KEYS
            or key in PAD_PARAM_KEYS
            or key in BASS_PARAM_KEYS
            or key in PERCUSSION_PARAM_KEYS
            or key in ORNAMENT_PARAM_KEYS
        ):
            dependent_widgets.setdefault(key, []).extend(row_widgets)
        ttk.Label(row, text=hint, foreground="gray").pack(side=tk.LEFT, padx=8)


def _update_dependent_states(vars_map: dict, dependent_widgets: dict) -> None:
    """根据各叠加层开关更新相关参数控件的可编辑状态。"""
    def _on(var_key: str) -> bool:
        v = vars_map.get(var_key)
        return v.get() if v is not None else False

    acc_on = _on("COMPOSE_ADD_ACCOMPANIMENT")
    cpt_on = _on("COMPOSE_ADD_COUNTERPOINT")
    pad_on = _on("COMPOSE_ADD_PAD")
    bass_on = _on("COMPOSE_ADD_BASS")
    perc_on = _on("COMPOSE_ADD_PERCUSSION")
    ornament_on = _on("COMPOSE_ADD_ORNAMENTATION")

    for key in ACCOMPANIMENT_PARAM_KEYS:
        state = "normal" if acc_on else "disabled"
        for w in dependent_widgets.get(key, []):
            try:
                w.configure(state=state)
            except tk.TclError:
                pass
    for key in COUNTERPOINT_PARAM_KEYS:
        state = "normal" if cpt_on else "disabled"
        for w in dependent_widgets.get(key, []):
            try:
                w.configure(state=state)
            except tk.TclError:
                pass
    for key in PAD_PARAM_KEYS:
        state = "normal" if pad_on else "disabled"
        for w in dependent_widgets.get(key, []):
            try:
                w.configure(state=state)
            except tk.TclError:
                pass
    for key in BASS_PARAM_KEYS:
        state = "normal" if bass_on else "disabled"
        for w in dependent_widgets.get(key, []):
            try:
                w.configure(state=state)
            except tk.TclError:
                pass
    for key in PERCUSSION_PARAM_KEYS:
        state = "normal" if perc_on else "disabled"
        for w in dependent_widgets.get(key, []):
            try:
                w.configure(state=state)
            except tk.TclError:
                pass
    for key in ORNAMENT_PARAM_KEYS:
        state = "normal" if ornament_on else "disabled"
        for w in dependent_widgets.get(key, []):
            try:
                w.configure(state=state)
            except tk.TclError:
                pass


def main() -> None:
    """打开控制面板窗口；操作开关键「生成并播放」后根据当前参数生成并播放。
    播放结束后控制面板不关闭，程序保持运行，直至用户关闭窗口。"""
    root = tk.Tk()
    root.title("Musician 参数控制面板")
    root.geometry("960x560")
    root.minsize(700, 400)

    # 强制 ttk 按钮文字颜色，缓解 macOS 上按钮未点击时文字不显示的问题
    try:
        ttk.Style().configure("TButton", foreground="black")
    except Exception:
        pass

    # 可滚动内容，内部分为左右两列（左：调性/动机/轨迹；右：作曲/播放/演示）
    canvas = tk.Canvas(root)
    scrollbar = ttk.Scrollbar(root)
    scrollable = ttk.Frame(canvas)
    def _on_scrollable_configure(e):
        canvas.configure(scrollregion=canvas.bbox("all"))
    scrollable.bind("<Configure>", _on_scrollable_configure)
    cwin = canvas.create_window((0, 0), window=scrollable, anchor=tk.NW)
    def _on_canvas_configure(e):
        canvas.itemconfig(cwin, width=e.width)
    canvas.bind("<Configure>", _on_canvas_configure)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.configure(command=canvas.yview)

    left_col = ttk.Frame(scrollable)
    right_col = ttk.Frame(scrollable)
    left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 8))
    right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

    vars_map: dict = {}
    kinds: dict = {}
    dependent_widgets: dict = {}
    for i, (title, params) in enumerate(PANEL_GROUPS):
        parent = left_col if i < _PANEL_LEFT_COLUMN_GROUPS else right_col
        _build_group(parent, title, params, vars_map, kinds, dependent_widgets)

    # 各叠加层开关控制对应参数的可编辑状态
    _update_dependent_states(vars_map, dependent_widgets)

    def _on_layer_toggle(*_args) -> None:
        _update_dependent_states(vars_map, dependent_widgets)

    for switch_key in (
        "COMPOSE_ADD_ACCOMPANIMENT",
        "COMPOSE_ADD_COUNTERPOINT",
        "COMPOSE_ADD_PAD",
        "COMPOSE_ADD_BASS",
        "COMPOSE_ADD_PERCUSSION",
        "COMPOSE_ADD_ORNAMENTATION",
    ):
        v = vars_map.get(switch_key)
        if v is not None:
            v.trace_add("write", _on_layer_toggle)

    # 面板参数防抖写回 conf.py
    _conf_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conf.py")
    _conf_py_after_id: list = [None]

    def _schedule_conf_py_write() -> None:
        if _conf_py_after_id[0] is not None:
            root.after_cancel(_conf_py_after_id[0])

        def _flush() -> None:
            _conf_py_after_id[0] = None
            try:
                _apply_panel_to_conf(vars_map, kinds)
                _write_conf_py_file(_conf_py_path, vars_map, kinds)
            except Exception:
                pass

        _conf_py_after_id[0] = root.after(CONF_PY_DEBOUNCE_MS, _flush)

    for var in vars_map.values():
        var.trace_add("write", lambda *a: _schedule_conf_py_write())

    # 监控 musician 目录下 .py 文件（除 conf.py），变更则重启应用
    _musician_dir = os.path.dirname(os.path.abspath(__file__))
    _watch_paths = [
        os.path.join(_musician_dir, f)
        for f in os.listdir(_musician_dir)
        if f.endswith(".py") and f != "conf.py"
    ]
    _watch_mtimes: dict = {}
    _restart_scheduled: list = [False]

    def _do_restart() -> None:
        if _restart_scheduled[0]:
            return
        _restart_scheduled[0] = True
        try:
            subprocess.Popen(
                [sys.executable, "-m", "musician"],
                cwd=os.getcwd(),
                env=os.environ,
            )
        finally:
            root.quit()

    def _watch_py_files() -> None:
        time.sleep(2.0)
        for p in _watch_paths:
            try:
                _watch_mtimes[p] = os.path.getmtime(p)
            except OSError:
                pass
        while True:
            time.sleep(WATCH_POLL_INTERVAL)
            changed = False
            for p in _watch_paths:
                try:
                    m = os.path.getmtime(p)
                    if _watch_mtimes.get(p) != m:
                        _watch_mtimes[p] = m
                        changed = True
                except OSError:
                    pass
            if changed:
                root.after(0, _do_restart)
                break

    threading.Thread(target=_watch_py_files, daemon=True).start()

    # 底部：开关键 + 状态
    bottom = ttk.Frame(root)
    bottom.pack(fill=tk.X, side=tk.BOTTOM, padx=8, pady=8)
    status_var = tk.StringVar(value="就绪")
    ttk.Label(bottom, textvariable=status_var).pack(side=tk.LEFT, padx=4)

    def on_play() -> None:
        _apply_panel_to_conf(vars_map, kinds)
        threading.Thread(target=_generate_and_play, args=(root, status_var), daemon=True).start()

    def on_export_ts_lib() -> None:
        try:
            path = export_ts_lib()
            status_var.set(f"已导出 TS 库: {path}")
        except Exception as e:
            status_var.set(f"导出 TS 库失败: {e}")

    def on_export_midi() -> None:
        def _do_export() -> None:
            root.after(0, lambda: status_var.set("正在生成并导出 MIDI…"))
            try:
                _apply_panel_to_conf(vars_map, kinds)
                trajectory = make_demo_trajectory(conf.DEMO_TRAJECTORY_LENGTH)
                seed = (time.time_ns() % (2**32)) ^ (os.getpid() % (2**32))
                motive = trajectory_to_motive(
                    trajectory,
                    target_length=conf.MOTIVE_TARGET_LENGTH,
                    base_duration=conf.MOTIVE_BASE_DURATION,
                    key_root_midi=getattr(conf, "KEY_ROOT_MIDI", 60),
                    key_mode=getattr(conf, "KEY_MODE", "major"),
                    seed=seed,
                    style=getattr(conf, "MOTIVE_STYLE", "default"),
                )
                import random
                rng = random.Random(seed)
                transpose = rng.randint(conf.DEMO_TRANSPOSE_MIN, conf.DEMO_TRANSPOSE_MAX)
                bpm = rng.randint(conf.DEMO_BPM_MIN, conf.DEMO_BPM_MAX)
                motive = [Note(pitch=max(0, min(127, n.pitch + transpose)), duration=n.duration, velocity=n.velocity, start=n.start) for n in motive]
                score = compose(
                    motive,
                    bpm=bpm,
                    add_accompaniment=getattr(conf, "COMPOSE_ADD_ACCOMPANIMENT", True),
                    accompaniment_velocity=getattr(conf, "COMPOSE_ACCOMPANIMENT_VELOCITY", 0.35),
                    accompaniment_style=getattr(conf, "COMPOSE_ACCOMPANIMENT_STYLE", "block"),
                    add_counterpoint=getattr(conf, "COMPOSE_ADD_COUNTERPOINT", False),
                    counterpoint_style=getattr(conf, "COMPOSE_COUNTERPOINT_STYLE", "parallel_3rd"),
                    add_pad=getattr(conf, "COMPOSE_ADD_PAD", False),
                    pad_velocity=getattr(conf, "COMPOSE_PAD_VELOCITY", 0.25),
                    pad_chord_duration=getattr(conf, "COMPOSE_PAD_CHORD_DURATION", 4.0),
                    pad_octave_offset=getattr(conf, "COMPOSE_PAD_OCTAVE_OFFSET", 1),
                    add_bass=getattr(conf, "COMPOSE_ADD_BASS", False),
                    bass_velocity=getattr(conf, "COMPOSE_BASS_VELOCITY", 0.4),
                    bass_style=getattr(conf, "COMPOSE_BASS_STYLE", "root_only"),
                    bass_octave_offset=getattr(conf, "COMPOSE_BASS_OCTAVE_OFFSET", -1),
                    add_percussion=getattr(conf, "COMPOSE_ADD_PERCUSSION", False),
                    percussion_velocity=getattr(conf, "COMPOSE_PERCUSSION_VELOCITY", 0.5),
                    percussion_pattern=getattr(conf, "COMPOSE_PERCUSSION_PATTERN", "simple_44"),
                    add_ornamentation=getattr(conf, "COMPOSE_ADD_ORNAMENTATION", False),
                    ornament_velocity_ratio=getattr(conf, "COMPOSE_ORNAMENT_VELOCITY_RATIO", 0.6),
                    ornament_density=getattr(conf, "COMPOSE_ORNAMENT_DENSITY", 0.3),
                    ornament_max_duration=getattr(conf, "COMPOSE_ORNAMENT_MAX_DURATION", 0.25),
                    key_root_midi=getattr(conf, "KEY_ROOT_MIDI", 60),
                    key_mode=getattr(conf, "KEY_MODE", "major"),
                )
                path = os.path.join(os.getcwd(), "musician_export.mid")
                export_score_to_midi(score, path)
                root.after(0, lambda: status_var.set(f"已导出: {path}"))
            except Exception as e:
                root.after(0, lambda: status_var.set(f"导出失败: {e}"))

        threading.Thread(target=_do_export, daemon=True).start()

    # macOS 上 ttk 按钮文字常不显示，底部三个键用 tk.Button 保证可见
    if sys.platform == "darwin":
        tk.Button(bottom, text="导出 TS 库", command=on_export_ts_lib).pack(side=tk.RIGHT, padx=(0, 8))
        tk.Button(bottom, text="导出 MIDI", command=on_export_midi).pack(side=tk.RIGHT, padx=(0, 8))
        tk.Button(bottom, text="生成并播放", command=on_play).pack(side=tk.RIGHT)
    else:
        ttk.Button(bottom, text="导出 TS 库", command=on_export_ts_lib).pack(side=tk.RIGHT, padx=(0, 8))
        ttk.Button(bottom, text="导出 MIDI", command=on_export_midi).pack(side=tk.RIGHT, padx=(0, 8))
        ttk.Button(bottom, text="生成并播放", command=on_play).pack(side=tk.RIGHT)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    root.bind("<MouseWheel>", _on_mousewheel)

    # 主循环：窗口保持打开，程序持续运行；播放在后台线程，结束后不退出
    root.mainloop()


if __name__ == "__main__":
    main()
