"""
作曲器：以动机为主题，添加伴奏（和声）、可选对位，生成完整乐谱。
"""
from typing import List, Optional

from . import conf
from .models import Motive, Note, Score, Track
from .tonality import get_progression_chords, interval_in_scale_steps, get_scale
from .groove import apply_groove


def compose(
    motive: Motive,
    bpm: float = conf.COMPOSE_DEFAULT_BPM,
    add_accompaniment: bool = True,
    accompaniment_velocity: float = conf.COMPOSE_ACCOMPANIMENT_VELOCITY,
    accompaniment_style: str = conf.COMPOSE_ACCOMPANIMENT_STYLE,
    add_counterpoint: bool = conf.COMPOSE_ADD_COUNTERPOINT,
    counterpoint_style: str = conf.COMPOSE_COUNTERPOINT_STYLE,
    key_root_midi: Optional[int] = None,
    key_mode: Optional[str] = None,
) -> Score:
    """
    由动机生成乐谱。
    - 动机轨：原样保留。
    - 伴奏轨：按调性 I-IV-V-I 生成，形态可选 block / arpeggiated / rhythm_pattern。
    - 对位轨（可选）：平行三度/六度或固定音型。
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

    if add_counterpoint and motive:
        cpt = _make_counterpoint(motive, k_root, k_mode, counterpoint_style)
        tracks.append(Track(name="counterpoint", notes=cpt))

    num = getattr(conf, "TIME_SIGNATURE_NUMERATOR", 4)
    denom = getattr(conf, "TIME_SIGNATURE_DENOMINATOR", 4)
    score = Score(bpm=bpm, time_signature=(num, denom), tracks=tracks)
    return apply_groove(score)


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
    """对位声部：平行三度/六度或固定音型。"""
    ratio = conf.COMPOSE_COUNTERPOINT_VELOCITY_RATIO
    if style == "parallel_3rd":
        return _counterpoint_parallel(motive, root_midi, mode, steps=2, velocity_ratio=ratio)
    if style == "parallel_6th":
        return _counterpoint_parallel(motive, root_midi, mode, steps=5, velocity_ratio=ratio)
    if style == "ostinato":
        return _counterpoint_ostinato(motive, root_midi, mode, velocity_ratio=ratio)
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
