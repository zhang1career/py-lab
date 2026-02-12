"""
作曲器：以动机为主题，添加伴奏（和声）、可选对位、Pad、低音、打击、装饰，生成完整乐谱。
"""
import random
from typing import List, Optional

from . import conf
from .models import Motive, Note, Score, Track
from .tonality import get_progression_chords, interval_in_scale_steps, get_scale, snap_pitch_to_scale
from .groove import apply_groove

# GM 鼓键
GM_KICK = 36
GM_SNARE = 38


def time_signature_to_beats_per_bar(num: int, denom: int) -> int:
    """
    根据拍号 (num/denom) 计算每小节强拍数。
    - 复合拍（denom=8 且 num 为 3 的倍数）：6/8→2, 9/8→3, 12/8→4, 3/8→1
    - 单拍（denom=2 或 4 等）：beats = num
    - 其他：num 作为 fallback
    """
    if denom == 8 and num > 0 and num % 3 == 0:
        return num // 3
    return max(1, num)
# C2 for percussion when playback mode is c2
PERCUSSION_C2_MIDI = 36


def compose(
    motive: Motive,
    bpm: float = conf.COMPOSE_DEFAULT_BPM,
    add_accompaniment: bool = True,
    accompaniment_velocity: float = conf.COMPOSE_ACCOMPANIMENT_VELOCITY,
    accompaniment_style: str = conf.COMPOSE_ACCOMPANIMENT_STYLE,
    add_counterpoint: bool = conf.COMPOSE_ADD_COUNTERPOINT,
    counterpoint_style: str = conf.COMPOSE_COUNTERPOINT_STYLE,
    add_pad: bool = getattr(conf, "COMPOSE_ADD_PAD", False),
    pad_velocity: float = getattr(conf, "COMPOSE_PAD_VELOCITY", 0.25),
    pad_chord_duration: float = getattr(conf, "COMPOSE_PAD_CHORD_DURATION", 4.0),
    pad_octave_offset: int = getattr(conf, "COMPOSE_PAD_OCTAVE_OFFSET", 1),
    add_bass: bool = getattr(conf, "COMPOSE_ADD_BASS", False),
    bass_velocity: float = getattr(conf, "COMPOSE_BASS_VELOCITY", 0.4),
    bass_style: str = getattr(conf, "COMPOSE_BASS_STYLE", "root_only"),
    bass_octave_offset: int = getattr(conf, "COMPOSE_BASS_OCTAVE_OFFSET", -1),
    add_percussion: bool = getattr(conf, "COMPOSE_ADD_PERCUSSION", False),
    percussion_velocity: float = getattr(conf, "COMPOSE_PERCUSSION_VELOCITY", 0.5),
    percussion_pattern: str = getattr(conf, "COMPOSE_PERCUSSION_PATTERN", "simple_44"),
    add_ornamentation: bool = getattr(conf, "COMPOSE_ADD_ORNAMENTATION", False),
    ornament_velocity_ratio: float = getattr(conf, "COMPOSE_ORNAMENT_VELOCITY_RATIO", 0.6),
    ornament_density: float = getattr(conf, "COMPOSE_ORNAMENT_DENSITY", 0.3),
    ornament_max_duration: float = getattr(conf, "COMPOSE_ORNAMENT_MAX_DURATION", 0.25),
    key_root_midi: Optional[int] = None,
    key_mode: Optional[str] = None,
    time_signature: Optional[tuple[int, int]] = None,
) -> Score:
    """
    由动机生成乐谱。
    - 动机轨：原样保留。
    - 伴奏轨：按调性 I-IV-V-I 生成，形态可选 block / arpeggiated / rhythm_pattern。
    - 对位/副旋律轨（可选）：平行三度/六度、固定音型或副旋律（应答句）。
    - Pad / 低音 / 打击 / 装饰轨（可选）。
    """
    k_root = key_root_midi if key_root_midi is not None else conf.KEY_ROOT_MIDI
    k_mode = key_mode if key_mode is not None else conf.KEY_MODE
    chords = get_progression_chords(k_root, k_mode)

    tracks: list[Track] = []

    motive_notes = [Note(pitch=n.pitch, duration=n.duration, velocity=n.velocity, start=n.start) for n in motive]
    tracks.append(Track(name="motive", notes=motive_notes))

    if add_accompaniment and motive:
        accomp = _make_accompaniment(motive, chords, accompaniment_velocity, accompaniment_style)
        tracks.append(Track(name="accompaniment", notes=accomp))

    if add_bass and motive:
        bass_notes = _make_bass(motive, chords, bass_velocity, bass_style, bass_octave_offset, k_root)
        tracks.append(Track(name="bass", notes=bass_notes))

    if add_pad and motive:
        pad_notes = _make_pad(motive, chords, pad_velocity, pad_chord_duration, pad_octave_offset, k_root)
        tracks.append(Track(name="pad", notes=pad_notes))

    if add_counterpoint and motive:
        cpt = _make_counterpoint(motive, k_root, k_mode, counterpoint_style)
        tracks.append(Track(name="counterpoint", notes=cpt))

    if add_ornamentation and motive:
        ornament_notes = _make_ornamentation(
            motive, k_root, k_mode, ornament_velocity_ratio, ornament_density, ornament_max_duration
        )
        tracks.append(Track(name="ornamentation", notes=ornament_notes))

    if time_signature is not None:
        num, denom = time_signature
    else:
        num = getattr(conf, "TIME_SIGNATURE_NUMERATOR", 4)
        denom = getattr(conf, "TIME_SIGNATURE_DENOMINATOR", 4)
    beats_per_bar = time_signature_to_beats_per_bar(num, denom)

    if add_percussion and motive:
        perc_notes = _make_percussion(motive, percussion_velocity, percussion_pattern, beats_per_bar)
        tracks.append(Track(name="percussion", notes=perc_notes))

    score = Score(bpm=bpm, time_signature=(num, denom), tracks=tracks)
    return apply_groove(score, beats_per_bar=beats_per_bar)


def _make_accompaniment(
    motive: Motive,
    chords: List[List[int]],
    velocity: float,
    style: str,
) -> list[Note]:
    """根据动机时间范围与和弦进行生成伴奏。"""
    if not motive:
        return []
    end_time = max(n.start + n.duration for n in motive)
    chord_duration = conf.COMPOSE_CHORD_DURATION

    if style == "arpeggiated":
        return _accomp_arpeggiated(motive, chords, end_time, chord_duration, velocity)
    if style == "rhythm_pattern":
        return _accomp_rhythm_pattern(motive, chords, end_time, chord_duration, velocity)
    return _accomp_block(chords, end_time, chord_duration, velocity)


def _accomp_block(
    chords: List[List[int]],
    end_time: float,
    chord_duration: float,
    velocity: float,
) -> list[Note]:
    """块状和弦：每 chord_duration 拍一个和弦。"""
    notes: list[Note] = []
    t = 0.0
    i = 0
    while t < end_time:
        for pitch in chords[i % len(chords)]:
            notes.append(Note(pitch=pitch, duration=chord_duration, velocity=velocity, start=t))
        t += chord_duration
        i += 1
    return notes


def _accomp_arpeggiated(
    motive: Motive,
    chords: List[List[int]],
    end_time: float,
    chord_duration: float,
    velocity: float,
) -> list[Note]:
    """分解和弦：每个和弦音依次以短时值发出。"""
    note_dur = conf.COMPOSE_ARPEGGIO_NOTE_DURATION
    notes: list[Note] = []
    t = 0.0
    i = 0
    while t < end_time:
        triad = chords[i % len(chords)]
        for j, pitch in enumerate(triad):
            notes.append(Note(pitch=pitch, duration=note_dur, velocity=velocity, start=t + j * note_dur))
        t += chord_duration
        i += 1
    return notes


def _accomp_rhythm_pattern(
    motive: Motive,
    chords: List[List[int]],
    end_time: float,
    chord_duration: float,
    velocity: float,
) -> list[Note]:
    """节奏型：强拍低音（根音）、弱拍和弦（三音+五音），每小节一个和弦。"""
    notes: list[Note] = []
    t = 0.0
    i = 0
    while t < end_time:
        triad = chords[i % len(chords)]
        root, third, fifth = triad[0], triad[1], triad[2]
        # 强拍：根音，持续半小节
        half = chord_duration / 2
        notes.append(Note(pitch=root, duration=half, velocity=velocity, start=t))
        # 弱拍：三音、五音各半拍（或合在一起）
        notes.append(Note(pitch=third, duration=half, velocity=velocity * 0.9, start=t + half))
        notes.append(Note(pitch=fifth, duration=half, velocity=velocity * 0.9, start=t + half))
        t += chord_duration
        i += 1
    return notes


def _make_counterpoint(
    motive: Motive,
    root_midi: int,
    mode: str,
    style: str,
) -> list[Note]:
    """对位声部：平行三度/六度、固定音型或副旋律（应答句）。"""
    ratio = conf.COMPOSE_COUNTERPOINT_VELOCITY_RATIO
    if style == "parallel_3rd":
        return _counterpoint_parallel(motive, root_midi, mode, steps=2, velocity_ratio=ratio)
    if style == "parallel_6th":
        return _counterpoint_parallel(motive, root_midi, mode, steps=5, velocity_ratio=ratio)
    if style == "ostinato":
        return _counterpoint_ostinato(motive, root_midi, mode, velocity_ratio=ratio)
    if style == "secondary_melody":
        return _counterpoint_secondary_melody(motive, root_midi, mode, velocity_ratio=ratio)
    return _counterpoint_parallel(motive, root_midi, mode, steps=2, velocity_ratio=ratio)


def _counterpoint_parallel(
    motive: Motive,
    root_midi: int,
    mode: str,
    steps: int,
    velocity_ratio: float,
) -> list[Note]:
    """平行音程：动机每个音上方 steps 个音阶音（2=三度，5=六度）。"""
    notes: list[Note] = []
    for n in motive:
        pitch = interval_in_scale_steps(root_midi, mode, n.pitch, steps)
        vel = max(0.0, min(1.0, n.velocity * velocity_ratio))
        notes.append(Note(pitch=pitch, duration=n.duration, velocity=vel, start=n.start))
    return notes


def _counterpoint_ostinato(
    motive: Motive,
    root_midi: int,
    mode: str,
    velocity_ratio: float,
) -> list[Note]:
    """固定音型：1 小节循环，调内 5-3-1-3 八分音符。"""
    scale = get_scale(mode)
    # 一个八度内：第 5、3、1、3 级（高到低再到高）
    # 半音：scale[4], scale[2], scale[0], scale[2]
    ostinato_semitones = [scale[4], scale[2], scale[0], scale[2]]
    note_dur = 0.5  # 半拍一个音
    notes: list[Note] = []
    end_time = max(n.start + n.duration for n in motive)
    t = 0.0
    idx = 0
    while t < end_time:
        sem = ostinato_semitones[idx % 4]
        # 用根音所在八度
        pitch = root_midi + 12 + sem
        if pitch > 127:
            pitch -= 12
        notes.append(Note(pitch=pitch, duration=note_dur, velocity=velocity_ratio, start=t))
        t += note_dur
        idx += 1
    return notes


def _counterpoint_secondary_melody(
    motive: Motive,
    root_midi: int,
    mode: str,
    velocity_ratio: float,
) -> list[Note]:
    """副旋律（应答句）：动机延迟 1 小节，时值略拉长、力度略弱，形成呼应。"""
    delay_beats = 4.0  # 1 小节
    duration_factor = 1.4
    notes: list[Note] = []
    for n in motive:
        start = n.start + delay_beats
        dur = min(n.duration * duration_factor, 2.0)
        vel = max(0.0, min(1.0, n.velocity * velocity_ratio * 0.9))
        pitch = snap_pitch_to_scale(n.pitch, root_midi, mode)
        notes.append(Note(pitch=pitch, duration=dur, velocity=vel, start=start))
    return notes


def _make_pad(
    motive: Motive,
    chords: List[List[int]],
    velocity: float,
    chord_duration: float,
    octave_offset: int,
    root_midi: int,
) -> list[Note]:
    """Pad：I-IV-V-I 长音铺底，每和弦三音持续 chord_duration 拍，音区根音上方 octave_offset 八度。"""
    if not motive:
        return []
    end_time = max(n.start + n.duration for n in motive)
    notes: list[Note] = []
    t = 0.0
    i = 0
    while t < end_time:
        triad = chords[i % len(chords)]
        # 三音（triad[1]）移到根音上方 octave_offset 八度
        pitch = root_midi + 12 * octave_offset + (triad[1] - root_midi) % 12
        pitch = max(0, min(127, pitch))
        notes.append(Note(pitch=pitch, duration=chord_duration, velocity=velocity, start=t))
        t += chord_duration
        i += 1
    return notes


def _make_bass(
    motive: Motive,
    chords: List[List[int]],
    velocity: float,
    style: str,
    octave_offset: int,
    root_midi: int,
) -> list[Note]:
    """低音线：按和弦进行每 chord_duration 根音（及可选五音）。"""
    if not motive:
        return []
    end_time = max(n.start + n.duration for n in motive)
    chord_duration = getattr(conf, "COMPOSE_CHORD_DURATION", 4.0)
    notes: list[Note] = []
    t = 0.0
    i = 0
    while t < end_time:
        triad = chords[i % len(chords)]
        bass_pitch = max(0, min(127, triad[0] + 12 * octave_offset))
        if style == "root_fifth":
            fifth_pitch = max(0, min(127, triad[2] + 12 * octave_offset))
            half = chord_duration / 2
            notes.append(Note(pitch=bass_pitch, duration=half, velocity=velocity, start=t))
            notes.append(Note(pitch=fifth_pitch, duration=half, velocity=velocity * 0.9, start=t + half))
        else:
            notes.append(Note(pitch=bass_pitch, duration=chord_duration, velocity=velocity, start=t))
        t += chord_duration
        i += 1
    return notes


def _make_percussion(
    motive: Motive,
    velocity: float,
    pattern: str,
    beats_per_bar: Optional[int] = None,
) -> list[Note]:
    """打击轨：simple_44 为 4/4 第 1、3 拍 kick，第 2、4 拍 snare。"""
    if not motive:
        return []
    end_time = max(n.start + n.duration for n in motive)
    if beats_per_bar is None:
        beats_per_bar = getattr(conf, "BEATS_PER_BAR", 4)
    notes: list[Note] = []
    t = 0.0
    step = 0.5
    while t < end_time:
        bar_pos = t % beats_per_bar
        if pattern == "simple_44":
            if bar_pos < 0.05 or (1.95 < bar_pos < 2.05):
                notes.append(Note(pitch=GM_KICK, duration=0.25, velocity=velocity, start=t))
            elif 0.95 < bar_pos < 1.05 or 2.95 < bar_pos < 3.05:
                notes.append(Note(pitch=GM_SNARE, duration=0.25, velocity=velocity * 0.85, start=t))
        t += step
    return notes


def _make_ornamentation(
    motive: Motive,
    root_midi: int,
    mode: str,
    velocity_ratio: float,
    density: float,
    max_duration: float,
) -> list[Note]:
    """装饰：在部分动机音后插入短装饰音（调内上下二度）。"""
    if not motive:
        return []
    notes: list[Note] = []
    scale = get_scale(mode)
    for i, n in enumerate(motive):
        if random.Random(i).random() >= density:
            continue
        # 在音结束后插入短音，音高为原音上方或下方一个音阶音
        start = n.start + n.duration
        dur = min(max_duration, 0.25)
        vel = max(0.0, min(1.0, n.velocity * velocity_ratio))
        up = interval_in_scale_steps(root_midi, mode, n.pitch, 1)
        down = interval_in_scale_steps(root_midi, mode, n.pitch, -1)
        pitch = up if (i % 2 == 0) else down
        notes.append(Note(pitch=pitch, duration=dur, velocity=vel, start=start))
    return notes
