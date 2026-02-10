"""
播放器：将乐谱渲染为音频并播放。
"""
import numpy as np

try:
    import simpleaudio as sa
except ImportError:
    sa = None

from . import conf
from .models import Score, Note


def midi_to_freq(midi: int) -> float:
    return conf.PLAYER_A4_FREQ * (2.0 ** ((midi - conf.PLAYER_A4_MIDI) / conf.PLAYER_SEMITONE_RATIO))


def play_score(score: Score, sample_rate: int = conf.PLAYER_SAMPLE_RATE) -> None:
    """将乐谱按拍转换为时间，混合所有音轨后播放。"""
    if sa is None:
        raise RuntimeError("需要安装 simpleaudio: pip install simpleaudio")
    beat_sec = 60.0 / score.bpm
    total_sec = score.total_duration()
    if total_sec <= 0:
        return
    n_samples = int(total_sec * sample_rate)
    buffer = np.zeros(n_samples, dtype=np.float32)
    for track in score.tracks:
        for note in track.notes:
            start_sec = note.start * beat_sec
            dur_sec = note.duration * beat_sec
            start_sample = int(start_sec * sample_rate)
            dur_samples = int(dur_sec * sample_rate)
            if start_sample < 0 or start_sample + dur_samples > n_samples:
                continue
            freq = midi_to_freq(note.pitch)
            t = np.linspace(0, dur_sec, dur_samples, False)
            # 简单正弦 + 力度
            wave = np.sin(2 * np.pi * freq * t) * note.velocity
            # 简单包络（前后淡入淡出减少咔嗒）
            fade = min(dur_samples // conf.PLAYER_FADE_DIVISOR, conf.PLAYER_FADE_MAX_SAMPLES)
            if fade > 0:
                wave[:fade] *= np.linspace(0, 1, fade)
                wave[-fade:] *= np.linspace(1, 0, fade)
            buffer[start_sample: start_sample + dur_samples] += wave
    peak = np.max(np.abs(buffer))
    if peak > 0:
        buffer = buffer / peak * conf.PLAYER_MASTER_GAIN
    audio = (buffer * conf.PLAYER_INT16_SCALE).astype(np.int16)
    play_obj = sa.play_buffer(audio, 1, 2, sample_rate)
    play_obj.wait_done()
