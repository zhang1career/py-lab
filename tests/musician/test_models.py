"""
测试 musician.models：TrajectoryPoint, Note, Track, Score。
"""
from musician.models import TrajectoryPoint, Note, Track, Score


def test_trajectory_point_immutable():
    """TrajectoryPoint 为 frozen，属性不可改。"""
    p = TrajectoryPoint(velocity=0.5, direction=90, intensity=0.8)
    assert p.velocity == 0.5 and p.direction == 90 and p.intensity == 0.8


def test_note_default_start():
    """Note 的 start 默认为 0。"""
    n = Note(pitch=60, duration=0.25, velocity=0.8)
    assert n.start == 0


def test_track_default_notes():
    """Track 默认 notes 为空列表。"""
    t = Track(name="melody")
    assert t.notes == []


def test_score_total_duration_empty():
    """空乐谱 total_duration 为 0。"""
    s = Score(bpm=120, tracks=[])
    assert s.total_duration() == 0.0


def test_score_total_duration_single_note():
    """单音符乐谱时长为该音符的 start + duration 换算成秒。"""
    beat_sec = 60.0 / 120
    s = Score(bpm=120, tracks=[Track(name="x", notes=[Note(60, 2.0, 0.8, start=0)])])
    assert abs(s.total_duration() - 2.0 * beat_sec) < 1e-6


def test_score_total_duration_multiple_tracks():
    """多轨时取所有音符中 end 的最大值。"""
    s = Score(bpm=60, tracks=[
        Track("a", notes=[Note(60, 1.0, 0.8, start=0)]),
        Track("b", notes=[Note(64, 2.0, 0.7, start=1.0)]),
    ])
    # 最长结束时间 = 1.0 + 2.0 = 3.0 拍
    assert abs(s.total_duration() - 3.0 * (60.0 / 60)) < 1e-6
