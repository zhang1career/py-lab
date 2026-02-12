"""
测试 musician.composer：动机 → 乐谱（动机轨、伴奏轨）。
"""
from musician.models import Note, Track
from musician.composer import compose, time_signature_to_beats_per_bar


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


def test_time_signature_to_beats_per_bar():
    """拍号 → 每小节强拍数：单拍用分子，复合拍（x/8）用 num/3。"""
    assert time_signature_to_beats_per_bar(4, 4) == 4
    assert time_signature_to_beats_per_bar(3, 4) == 3
    assert time_signature_to_beats_per_bar(2, 4) == 2
    assert time_signature_to_beats_per_bar(2, 2) == 2
    assert time_signature_to_beats_per_bar(6, 8) == 2  # compound duple
    assert time_signature_to_beats_per_bar(9, 8) == 3  # compound triple
    assert time_signature_to_beats_per_bar(12, 8) == 4  # compound quadruple
    assert time_signature_to_beats_per_bar(3, 8) == 1
