"""
测试 musician.trajectory_to_motive：轨迹 → 动机的映射与随机性。
"""
from tests.musician.conftest import make_trajectory, motive_signature
from musician.trajectory_to_motive import trajectory_to_motive


def test_same_trajectory_different_seeds_gives_different_motive():
    """相同运动轨迹、不同 seed 时，应得到不同的旋律结果。"""
    trajectory = make_trajectory(32)
    target = 16

    motive_a = trajectory_to_motive(trajectory, target_length=target, seed=1)
    motive_b = trajectory_to_motive(trajectory, target_length=target, seed=2)
    motive_c = trajectory_to_motive(trajectory, target_length=target, seed=99999)

    sig_a = motive_signature(motive_a)
    sig_b = motive_signature(motive_b)
    sig_c = motive_signature(motive_c)

    assert sig_a != sig_b
    assert sig_a != sig_c
    assert sig_b != sig_c


def test_same_trajectory_different_seeds_print_pitches(capsys):
    """同一轨迹 seed=1 与 seed=2 的音高序列会打印到终端，便于肉眼确认不同。运行: pytest tests/musician/test_trajectory_to_motive.py::test_same_trajectory_different_seeds_print_pitches -s"""
    trajectory = make_trajectory(32)
    target = 12

    motive_1 = trajectory_to_motive(trajectory, target_length=target, seed=1)
    motive_2 = trajectory_to_motive(trajectory, target_length=target, seed=2)

    pitches_1 = [n.pitch for n in motive_1]
    pitches_2 = [n.pitch for n in motive_2]

    assert pitches_1 != pitches_2, "同一轨迹不同 seed 应得到不同音高序列"
    # 打印到 stdout，用 pytest -s 可见
    print("\n同一轨迹 → 不同 seed 得到不同旋律（前 12 个音高 MIDI）:")
    print("  seed=1 音高:", pitches_1)
    print("  seed=2 音高:", pitches_2)


def test_same_trajectory_same_seed_gives_same_motive():
    """相同运动轨迹、相同 seed 时，应得到完全可复现的相同动机。"""
    trajectory = make_trajectory(24)
    target = 12

    motive_1 = trajectory_to_motive(trajectory, target_length=target, seed=42)
    motive_2 = trajectory_to_motive(trajectory, target_length=target, seed=42)

    assert motive_signature(motive_1) == motive_signature(motive_2)


def test_same_trajectory_multiple_different_seeds_all_differ():
    """同一轨迹用多个不同 seed 生成多段动机，两两不应完全相同。"""
    trajectory = make_trajectory(20)
    target = 10
    seeds = [0, 1, 2, 3, 4]
    motives = [trajectory_to_motive(trajectory, target_length=target, seed=s) for s in seeds]
    sigs = [motive_signature(m) for m in motives]

    for i in range(len(sigs)):
        for j in range(i + 1, len(sigs)):
            assert sigs[i] != sigs[j], f"seed={seeds[i]} 与 seed={seeds[j]} 应对同一轨迹产生不同动机"


def test_empty_trajectory_returns_empty_motive():
    """空轨迹应得到空动机。"""
    assert trajectory_to_motive([], target_length=64) == []


def test_arbitrary_length_trajectory_produces_fixed_length_motive():
    """任意长度轨迹应产生固定长度（target_length）的动机。"""
    for n in [1, 8, 32, 64, 128]:
        trajectory = make_trajectory(n)
        motive = trajectory_to_motive(trajectory, target_length=64, seed=0)
        assert len(motive) == 64, f"轨迹长度 {n} 应得到 64 个音"


def test_single_point_trajectory_produces_target_length_motive():
    """单点轨迹应生成 target_length 个音（通过随机扩展）。"""
    trajectory = make_trajectory(1)
    motive = trajectory_to_motive(trajectory, target_length=32, seed=7)
    assert len(motive) == 32
    assert all(0 <= n.pitch <= 127 for n in motive)


def test_motive_notes_have_valid_pitch_and_times():
    """动机中每个音符的音高、时值、力度在合理范围内，且 start 单调递增。"""
    trajectory = make_trajectory(16)
    motive = trajectory_to_motive(trajectory, target_length=8, seed=0)
    assert len(motive) == 8
    for n in motive:
        assert 0 <= n.pitch <= 127
        assert n.duration > 0
        assert 0 <= n.velocity <= 1
    for i in range(1, len(motive)):
        assert motive[i].start >= motive[i - 1].start
