"""
播放器：将乐谱渲染为音频并播放。
支持泛音、ADSR 包络与可选 scipy 卷积混响。
"""
import numpy as np

try:
    import simpleaudio as sa
except ImportError:
    sa = None

try:
    from scipy import signal as scipy_signal
except ImportError:
    scipy_signal = None

from . import conf
from .models import Score, Note


def midi_to_freq(midi: int) -> float:
    return conf.PLAYER_A4_FREQ * (2.0 ** ((midi - conf.PLAYER_A4_MIDI) / conf.PLAYER_SEMITONE_RATIO))


def _adsr_envelope(n_samples: int, sample_rate: int, velocity: float) -> np.ndarray:
    """生成 ADSR 包络 [0,1]，长度 n_samples。音符过短时各段自动截断，避免越界。"""
    attack_sec = getattr(conf, "PLAYER_ATTACK_SEC", 0.01)
    decay_sec = getattr(conf, "PLAYER_DECAY_SEC", 0.05)
    sustain_level = getattr(conf, "PLAYER_SUSTAIN_LEVEL", 0.7)
    release_sec = getattr(conf, "PLAYER_RELEASE_SEC", 0.05)

    attack_n = min(int(attack_sec * sample_rate), n_samples)
    decay_n = min(int(decay_sec * sample_rate), max(0, n_samples - attack_n))
    release_n = min(int(release_sec * sample_rate), max(0, n_samples - attack_n - decay_n))
    sustain_n = max(0, n_samples - attack_n - decay_n - release_n)

    env = np.zeros(n_samples, dtype=np.float32)
    pos = 0
    if attack_n > 0:
        env[pos : pos + attack_n] = np.linspace(0, 1, attack_n)
        pos += attack_n
    if decay_n > 0:
        env[pos : pos + decay_n] = np.linspace(1, sustain_level, decay_n)
        pos += decay_n
    if sustain_n > 0:
        env[pos : pos + sustain_n] = sustain_level
        pos += sustain_n
    if release_n > 0 and pos < n_samples:
        release_actual = min(release_n, n_samples - pos)
        env[pos : pos + release_actual] = np.linspace(sustain_level, 0, release_actual)

    return env * velocity


def _tone_with_overtones(freq: float, t: np.ndarray, velocity: float) -> np.ndarray:
    """基波 + 二次、三次泛音。"""
    o2 = getattr(conf, "PLAYER_OVERTONE_2_RATIO", 0.5)
    o3 = getattr(conf, "PLAYER_OVERTONE_3_RATIO", 0.33)
    wave = np.sin(2 * np.pi * freq * t)
    wave += o2 * np.sin(2 * np.pi * 2 * freq * t)
    wave += o3 * np.sin(2 * np.pi * 3 * freq * t)
    norm = 1.0 + o2 + o3
    return (wave / norm) * velocity


def _apply_reverb(buffer: np.ndarray, sample_rate: int) -> np.ndarray:
    """可选：scipy 卷积混响。无 scipy 时返回原 buffer。"""
    if scipy_signal is None:
        return buffer
    wet = getattr(conf, "PLAYER_REVERB_WET", 0.2)
    length_sec = getattr(conf, "PLAYER_REVERB_LENGTH_SEC", 0.4)
    if wet <= 0 or length_sec <= 0:
        return buffer
    ir_len = int(length_sec * sample_rate)
    # 简单指数衰减 IR 模拟房间混响
    t = np.arange(ir_len, dtype=np.float32) / sample_rate
    ir = np.exp(-t * 8.0) * (np.random.RandomState(42).randn(ir_len).astype(np.float32))
    ir = ir / (np.sqrt(np.sum(ir * ir)) + 1e-8)
    out = scipy_signal.fftconvolve(buffer, ir, mode="same")
    out = out.astype(np.float32)
    return (1.0 - wet) * buffer + wet * out


def play_score(score: Score, sample_rate: int = conf.PLAYER_SAMPLE_RATE, use_reverb: bool = True) -> None:
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
            wave = _tone_with_overtones(freq, t, 1.0)
            env = _adsr_envelope(dur_samples, sample_rate, note.velocity)
            wave = wave * env
            buffer[start_sample : start_sample + dur_samples] += wave
    if use_reverb:
        buffer = _apply_reverb(buffer, sample_rate)
    peak = np.max(np.abs(buffer))
    if peak > 0:
        buffer = buffer / peak * conf.PLAYER_MASTER_GAIN
    audio = (buffer * conf.PLAYER_INT16_SCALE).astype(np.int16)
    play_obj = sa.play_buffer(audio, 1, 2, sample_rate)
    play_obj.wait_done()
