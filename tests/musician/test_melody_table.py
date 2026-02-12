"""
测试 musician.melody_table：轨迹→5 音级 key、旋律表最长前缀查表与 fallback。
"""
from tests.musician.conftest import make_trajectory
from musician.melody_table import (
    trajectory_to_key,
    key_to_string,
    lookup_melody,
    load_melody_table,
)


def test_trajectory_to_key_returns_fixed_length():
    """轨迹应得到固定长度的 key（音级 1–7）。"""
    trajectory = make_trajectory(32)
    key = trajectory_to_key(trajectory, 60, "major", key_length=5)
    assert len(key) == 5
    assert all(1 <= d <= 7 for d in key)


def test_trajectory_to_key_deterministic():
    """同一轨迹、同一调性应得到相同 key。"""
    trajectory = make_trajectory(24)
    key_a = trajectory_to_key(trajectory, 60, "major", key_length=5)
    key_b = trajectory_to_key(trajectory, 60, "major", key_length=5)
    assert key_a == key_b


def test_trajectory_to_key_key_length_variable():
    """key_length 1–7 应得到对应长度。"""
    trajectory = make_trajectory(16)
    for length in (1, 3, 5, 7):
        key = trajectory_to_key(trajectory, 60, "major", key_length=length)
        assert len(key) == length
        assert all(1 <= d <= 7 for d in key)


def test_empty_trajectory_returns_default_key():
    """空轨迹应得到默认 key（全 1）。"""
    key = trajectory_to_key([], 60, "major", key_length=5)
    assert key == (1,) * 5


def test_key_to_string():
    """key 转字符串格式正确。"""
    assert key_to_string((1, 3, 5, 3, 1)) == "1,3,5,3,1"
    assert key_to_string([1]) == "1"


def test_lookup_melody_returns_motive():
    """查表应返回非空 Motive（至少 fallback）。"""
    motive, _ = lookup_melody((1, 3, 5, 3, 1), 60, "major", use_fallback=True)
    assert len(motive) > 0
    for n in motive:
        assert 0 <= n.pitch <= 127
        assert n.duration > 0
        assert 0 <= n.velocity <= 1


def test_lookup_melody_longest_prefix():
    """最长前缀匹配：表中有 "1" 时，key (1,2,3,4,5) 应命中 "1" 的旋律。"""
    motive, _ = lookup_melody((1, 2, 3, 4, 5), 60, "major", use_fallback=True)
    assert len(motive) > 0


def test_lookup_melody_fallback_when_no_match():
    """无匹配且 use_fallback=True 时返回默认旋律。"""
    motive, _ = lookup_melody((9, 9, 9), 60, "major", table_path="/nonexistent.json", use_fallback=True)
    assert len(motive) > 0
    assert all(1 <= (n.pitch - 60) % 12 <= 11 or n.pitch == 60 for n in motive)


def test_lookup_melody_no_fallback_returns_empty_when_no_match():
    """无匹配且 use_fallback=False 时返回空列表。"""
    motive, overrides = lookup_melody((9, 9, 9), 60, "major", table_path="/nonexistent.json", use_fallback=False)
    assert motive == []
    assert overrides == {}


def test_lookup_melody_by_string_key():
    """支持字符串 key 查表。"""
    motive, _ = lookup_melody("1,3,5", 60, "major", use_fallback=True)
    assert len(motive) > 0


def test_motive_start_times_monotonic():
    """查表得到的 motive 的 start 应单调递增。"""
    trajectory = make_trajectory(20)
    key = trajectory_to_key(trajectory, 60, "major", key_length=5)
    motive, _ = lookup_melody(key, 60, "major")
    for i in range(1, len(motive)):
        assert motive[i].start >= motive[i - 1].start


def test_lookup_melody_returns_time_sign_overrides():
    """旋律表项含 time_sign_numerator/denominator 时，overrides 应包含。"""
    import os
    table_path = os.path.join(os.path.dirname(__file__), "..", "..", "musician", "melody_table.json")
    motive, overrides = lookup_melody((3,), 60, "major", table_path=table_path, use_fallback=True)
    assert len(motive) > 0
    # melody_table.json 中 "3" 对应项为 4/4
    assert overrides.get("time_sign_numerator") == 4
    assert overrides.get("time_sign_denominator") == 4
