"""
测试 musician.player：midi_to_freq、play_score 行为（不实际播放音频）。
"""
from musician.models import Track, Score
from musician.player import midi_to_freq


def test_midi_to_freq_a440():
    """A4 (MIDI 69) 应为 440 Hz。"""
    assert abs(midi_to_freq(69) - 440.0) < 1e-6


def test_midi_to_freq_octave_ratio():
    """高八度应为 2 倍频率。"""
    f_low = midi_to_freq(60)
    f_high = midi_to_freq(72)
    assert abs(f_high / f_low - 2.0) < 1e-6


def test_midi_to_freq_c4():
    """C4 (MIDI 60) 约为 261.6 Hz。"""
    assert 261 < midi_to_freq(60) < 262


def test_play_score_empty_score_returns_early():
    """空乐谱或时长为 0 时 play_score 应直接返回不报错。"""
    from musician.player import play_score
    s = Score(bpm=120, tracks=[])
    play_score(s)  # 不应抛错；内部 total_duration()==0 会 return


def test_play_score_zero_duration_track():
    """仅有空轨时 total_duration 为 0，play_score 不崩溃。"""
    from musician.player import play_score
    s = Score(bpm=120, tracks=[Track(name="motive", notes=[])])
    play_score(s)
