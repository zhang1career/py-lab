# Musician：轨迹作曲与演奏

根据**空间运动轨迹**（速度、方向、力度）生成动机，经作曲处理（伴奏、对位等）得到乐谱，再播放。

---

## 架构设计

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  轨迹 (Input)   │ ──► │  动机 (Motive)   │ ──► │  乐谱 (Score)   │
│ velocity        │     │ 旋律轮廓/节奏/力度 │     │ 多声部事件序列   │
│ direction       │     │                  │     │                 │
│ intensity       │     └────────┬─────────┘     └────────┬────────┘
└─────────────────┘              │                        │
                                 │ 作曲器                  │ 播放器
                                 │ (伴奏/对位/和声)         │
                                 ▼                        ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  composer        │     │  player          │
                        │  - 动机声部       │     │  - 合成/采样     │
                        │  - 伴奏声部       │     │  - 实时或导出    │
                        │  - 对位声部(可选) │     └─────────────────┘
                        └──────────────────┘
```

### 模块职责

| 模块 | 职责 | 输入/输出 |
|------|------|-----------|
| **models** | 轨迹点、轨迹、音符、乐谱等数据结构 | - |
| **trajectory_to_motive** | 将轨迹映射为动机（音高轮廓、节奏、力度） | Trajectory → Motive |
| **composer** | 以动机为主题，生成伴奏、对位，输出完整乐谱 | Motive + 参数 → Score |
| **player** | 将乐谱渲染为音频并播放（或导出） | Score → 播放/文件 |

### 数据流

1. **Trajectory**：`[(velocity, direction, intensity), ...]`  
   - 可归一化到 0–1 或指定范围。
2. **Motive**：旋律片段，如 `[(pitch, duration, velocity), ...]`，带可选节奏型。
3. **Score**：多轨事件，每轨为 `(start_time, pitch, duration, velocity)` 列表，支持动机轨、伴奏轨、对位轨。

---

## 开发路线图

### Phase 1：最小可用（MVP）✅
- [x] 定义 Trajectory / Note / Score 模型
- [x] 轨迹 → 动机：速度→节奏密度，方向→音高走向，力度→velocity
- [x] 作曲器：动机 + 简单和声伴奏（块状和弦）
- [x] 播放器：Score → 正弦/简单合成 → simpleaudio 播放
- [x] 命令行或脚本端到端演示

### Phase 2：音乐性增强
- [ ] 调性约束（大调/小调、调号）
- [ ] 更丰富的伴奏（分解和弦、节奏型）
- [ ] 简单对位（二声部，如平行三/六度或固定音型）
- [ ] 乐谱导出（如 MIDI 或 MusicXML）

### Phase 3：扩展与优化
- [ ] 更多轨迹映射策略（不同风格）
- [ ] 小节/拍号、重音与律动
- [ ] 音色与混响（更好听）
- [ ] 可选 GUI：轨迹绘制 → 试听 → 导出

---

## 使用方式

### 最小示例

```bash
# 在项目根目录
python -m musician
```

或传入轨迹数据（见 `musician/__main__.py`）自定义 `velocity, direction, intensity` 数组后调用 `trajectory_to_motive` → `composer` → `player`。

### 依赖

- Python 3.8+
- numpy, simpleaudio（见项目根目录 `requirements.txt`）

---

## 目录结构

```
musician/
├── README.md              # 本文件（架构 + 路线图）
├── __init__.py
├── __main__.py            # 入口与最小演示
├── models.py              # Trajectory, Note, Score 等
├── trajectory_to_motive.py # 轨迹 → 动机
├── composer.py            # 动机 + 伴奏 → Score
└── player.py              # Score → 播放
```
