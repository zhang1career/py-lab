"""
将 Score 导出为 MIDI 文件。
"""
from pathlib import Path
from typing import Union

try:
    from midiutil import MIDIFile
except ImportError:
    MIDIFile = None

from .models import Score


def export_score_to_midi(
    score: Score,
    path: Union[str, Path],
    ticks_per_beat: int = 480,
) -> None:
    """
    将乐谱写入 MIDI 文件（格式 1，多轨）。
    时间单位使用乐谱的拍（beat），BPM 写入 tempo track。
    """
    if MIDIFile is None:
        raise RuntimeError("需要安装 MIDIUtil: pip install MIDIUtil")

    path = Path(path)
    # 格式 1：1 个 tempo track + 每轨一个 track
    num_tracks = 1 + len(score.tracks)
    midi = MIDIFile(num_tracks=num_tracks)
    track_index = 0
    midi.addTempo(track_index, 0, score.bpm)
    track_index += 1

    for track in score.tracks:
        for note in track.notes:
            # time, duration 为拍（beat）
            volume = int(max(0, min(127, note.velocity * 127)))
            midi.addNote(track_index, 0, note.pitch, note.start, note.duration, volume)
        track_index += 1

    with path.open("wb") as f:
        midi.writeFile(f)
