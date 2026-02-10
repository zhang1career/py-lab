"""
作曲器：以动机为主题，添加伴奏（和声）、可选对位，生成完整乐谱。
"""
from . import conf
from .models import Motive, Note, Score, Track


def compose(
    motive: Motive,
    bpm: float = conf.COMPOSE_DEFAULT_BPM,
    add_accompaniment: bool = True,
    accompaniment_velocity: float = conf.COMPOSE_ACCOMPANIMENT_VELOCITY,
) -> Score:
    """
    由动机生成乐谱。
    - 动机轨：原样保留，时间单位视为拍 (beat)。
    - 伴奏轨：根据动机轮廓生成简单块状和弦（每拍或每两拍一个和弦）。
    """
    tracks: list[Track] = []

    # 动机轨（已有 start, duration 为拍）
    motive_notes = [Note(pitch=n.pitch, duration=n.duration, velocity=n.velocity, start=n.start) for n in motive]
    tracks.append(Track(name="motive", notes=motive_notes))

    if add_accompaniment and motive:
        accomp = _make_accompaniment(motive, accompaniment_velocity)
        tracks.append(Track(name="accompaniment", notes=accomp))

    return Score(bpm=bpm, tracks=tracks)


def _make_accompaniment(motive: Motive, velocity: float) -> list[Note]:
    """根据动机时间范围生成简单和声伴奏（C 大调 I-IV-V-I 块状和弦）。"""
    if not motive:
        return []
    end_time = max(n.start + n.duration for n in motive)
    chord_duration = conf.COMPOSE_CHORD_DURATION
    chords = conf.COMPOSE_CHORDS
    notes: list[Note] = []
    t = 0.0
    i = 0
    while t < end_time:
        for pitch in chords[i % len(chords)]:
            notes.append(Note(pitch=pitch, duration=chord_duration, velocity=velocity, start=t))
        t += chord_duration
        i += 1
    return notes
