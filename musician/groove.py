"""
律动：4/4 强拍重音（velocity）与八分摇摆（swing）。
在作曲器输出上应用，使 MIDI 与播放一致。
"""
from . import conf
from .models import Note, Score, Track


def apply_groove(score: Score) -> Score:
    """
    对乐谱应用强拍重音与摇摆感，返回新 Score（不修改原 score）。
    - 强拍重音：每小节第一拍（start % beats_per_bar < 小量）的 velocity 乘以系数，上限 1.0。
    - 摇摆：落在「每拍后半八分」上的音符（如 0.5, 1.5, 2.5 拍）将 start 延后。
    """
    beats_per_bar = getattr(conf, "BEATS_PER_BAR", 4)
    accent_factor = getattr(conf, "GROOVE_ACCENT_STRONG_BEAT_FACTOR", 1.25)
    swing_amount = getattr(conf, "GROOVE_SWING_AMOUNT", 0.25)
    # 判定「强拍」的容差：start 在 bar_start 附近
    accent_tolerance = 0.05

    new_tracks: list[Track] = []
    for track in score.tracks:
        new_notes: list[Note] = []
        for n in track.notes:
            vel = n.velocity
            start = n.start
            # 强拍重音
            bar_pos = start % beats_per_bar
            if bar_pos < accent_tolerance:
                vel = min(1.0, vel * accent_factor)
            # 八分摇摆：第二个八分（0.5, 1.5, 2.5, ...）延后
            half_beat = 0.5
            # 是否落在「奇数八分」上：即 (start * 2) 舍入后为奇数
            half_beat_index = round(start * 2)
            if half_beat_index % 2 == 1:
                start = start + swing_amount * half_beat
            new_notes.append(Note(pitch=n.pitch, duration=n.duration, velocity=vel, start=start))
        new_tracks.append(Track(name=track.name, notes=new_notes))

    return Score(
        bpm=score.bpm,
        time_signature=score.time_signature,
        tracks=new_tracks,
    )
