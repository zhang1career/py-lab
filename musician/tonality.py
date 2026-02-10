"""
调性：音阶、调内音、I-IV-V-I 和弦。
供 melody_table（轨迹→key、查表）与 composer（和声）共用。
"""
from typing import List, Tuple

# 大调音阶（相对根音的半音偏移，一个八度）
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
# 自然小调
NATURAL_MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]

# I-IV-V 在音阶中的级数（0-based index）
DEGREE_I, DEGREE_IV, DEGREE_V = 0, 3, 4
# I-IV-V-I 进行
PROGRESSION_DEGREES = [DEGREE_I, DEGREE_IV, DEGREE_V, DEGREE_I]


def get_scale(mode: str) -> List[int]:
    """返回调式音阶（一个八度内相对根音的半音偏移）。"""
    if mode == "minor":
        return list(NATURAL_MINOR_SCALE)
    return list(MAJOR_SCALE)


def scale_degree_to_semitone(degree: int, mode: str) -> int:
    """音阶级数 (0-6) 转为相对根音的半音数（可超八度）。"""
    scale = get_scale(mode)
    octaves = degree // 7
    idx = degree % 7
    return octaves * 12 + scale[idx]


def get_triad_semitones(degree_index: int, mode: str) -> Tuple[int, int, int]:
    """
    返回 I/IV/V 三和弦相对根音的半音偏移 (根, 三, 五)。
    degree_index: 0=I, 3=IV, 4=V。
    大调三和弦均为大三；自然小调 i/iv/v 均为小三。
    """
    root = scale_degree_to_semitone(degree_index, mode)
    # 自然小调下 I、IV、V 均为小三和弦
    if mode == "minor":
        return (root, root + 3, root + 7)
    return (root, root + 4, root + 7)


def get_progression_chords(root_midi: int, mode: str) -> List[List[int]]:
    """I-IV-V-I 进行，每个和弦为 [pitch, pitch, pitch] 的 MIDI 列表。"""
    chords: List[List[int]] = []
    for deg in PROGRESSION_DEGREES:
        r, t, f = get_triad_semitones(deg, mode)
        chords.append([
            root_midi + r,
            root_midi + t,
            root_midi + f,
        ])
    return chords


def get_scale_midi_set(root_midi: int, mode: str, octaves: int = 3) -> set:
    """根音上下 octaves 个八度内的调内 MIDI 音高集合（用于 snap）。"""
    scale = get_scale(mode)
    out = set()
    for o in range(-octaves, octaves + 1):
        for s in scale:
            p = root_midi + o * 12 + s
            if 0 <= p <= 127:
                out.add(p)
    return out


def snap_pitch_to_scale(pitch: int, root_midi: int, mode: str) -> int:
    """将 MIDI 音高 snap 到最近调内音。"""
    scale_set = get_scale_midi_set(root_midi, mode)
    if pitch in scale_set:
        return pitch
    # 在上下半音范围内找最近调内音
    for d in range(1, 12):
        if pitch + d <= 127 and pitch + d in scale_set:
            return pitch + d
        if pitch - d >= 0 and pitch - d in scale_set:
            return pitch - d
    return max(0, min(127, pitch))


def interval_in_scale_steps(root_midi: int, mode: str, from_pitch: int, steps: int) -> int:
    """
    从 from_pitch 在调内向上数 steps 个音阶音，返回 MIDI 音高。
    steps > 0 向上，steps < 0 向下。用于平行三度/六度（steps=2 或 5）。
    """
    scale = get_scale(mode)
    base = snap_pitch_to_scale(from_pitch, root_midi, mode)
    rel = base - root_midi
    rel_semitone = ((rel % 12) + 12) % 12
    degree_in_octave = 0
    for i, s in enumerate(scale):
        if (rel_semitone - s) % 12 == 0:
            degree_in_octave = i
            break
    octave_offset = (base - root_midi) // 12
    if base - root_midi < 0 and (base - root_midi) % 12 != 0:
        octave_offset -= 1
    total_degrees = octave_offset * 7 + degree_in_octave + steps
    new_oct = total_degrees // 7
    new_idx = total_degrees % 7
    if new_idx < 0:
        new_idx += 7
        new_oct -= 1
    semitone = new_oct * 12 + scale[new_idx]
    return max(0, min(127, root_midi + semitone))
