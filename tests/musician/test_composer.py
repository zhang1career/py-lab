"""
测试 musician.composer：动机 → 乐谱（动机轨、伴奏轨）。
"""
from musician.models import Note, Track
from musician.composer import compose


def _make_motive(length: int):
    """构造长度为 length 的简单动机（不依赖 trajectory_to_motive）。"""
    notes = []
    t = 0.0
    for i in range(length):
        notes.append(Note(pitch=60 + (i % 5), duration=0.25, velocity=0.8, start=t))
        t += 0.25
    return notes


def test_compose_produces_score_with_motive_track():
    """作曲器应产出包含动机轨的乐谱。"""
    motive = _make_motive(8)
    score = compose(motive, bpm=120, add_accompaniment=True)
    assert len(score.tracks) >= 1
    assert any(t.name == "motive" for t in score.tracks)
    motive_track = next(t for t in score.tracks if t.name == "motive")
    assert len(motive_track.notes) == 8


def test_compose_with_accompaniment_has_two_tracks():
    """开启伴奏时乐谱应至少包含动机轨与伴奏轨。"""
    motive = _make_motive(4)
    score = compose(motive, add_accompaniment=True)
    assert len(score.tracks) >= 2
    names = {t.name for t in score.tracks}
    assert "motive" in names and "accompaniment" in names


def test_compose_without_accompaniment_single_track():
    """不开启伴奏且关闭其他轨时只有动机轨。"""
    motive = _make_motive(4)
    score = compose(
        motive,
        add_accompaniment=False,
        add_pad=False,
        add_bass=False,
        add_counterpoint=False,
        add_ornamentation=False,
        add_percussion=False,
    )
    assert len(score.tracks) == 1
    assert score.tracks[0].name == "motive"


def test_compose_empty_motive_no_accompaniment():
    """空动机时仍有一轨动机（空），无伴奏轨。"""
    score = compose([], add_accompaniment=True)
    assert len(score.tracks) == 1
    assert score.tracks[0].name == "motive"
    assert len(score.tracks[0].notes) == 0
