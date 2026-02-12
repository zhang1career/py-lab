# musician-ts-lib

由运动轨迹与可调参数生成乐谱的 TypeScript 库，适配 React Native（无 Node 专有 API）。

## 安装

```bash
npm install
npm run build
```

或在 monorepo 中直接引用 `src/` 下的 TypeScript 源码。

## API

### `trajectoryToScore(trajectory, params?, seed?)`

- **trajectoryOrKey**: `TrajectoryPoint[]` 或 `number[]` — 运动轨迹（每点 `{ velocity, direction, intensity }`）或一串音级 key（1–7），后者直接查旋律表
- **params**: `Params`（可选）— 与 Python `conf` 同名的键，如 `{ MELODY_KEY_LENGTH: 5, KEY_MODE: "minor" }`；可传 `MELODY_TABLE` 使用运行时加载的旋律表
- **返回**: `Score` — `{ bpm, time_signature, tracks: { name, notes: { pitch, duration, velocity, start }[] }[] }`

### 运行时加载旋律表 (melody_table.json)

默认使用库内嵌的旋律表；若需与 Python 侧共用 `melody_table.json`，可在 TS 侧加载 JSON 后通过 `params.MELODY_TABLE` 传入：

```ts
import { trajectoryToScore, parseMelodyTableFromJson } from "musician-ts-lib";

// 方式一：fetch 后解析
const res = await fetch("/path/to/melody_table.json");
const json = await res.text();
const melodyTable = parseMelodyTableFromJson(json);
const score = trajectoryToScore(trajectory, { MELODY_TABLE: melodyTable });

// 方式二：已读入的 JSON 字符串
const melodyTable = parseMelodyTableFromJson(jsonString);
const score = trajectoryToScore(trajectory, { MELODY_TABLE: melodyTable });
```

### 类型

- `TrajectoryPoint`: `{ velocity: number; direction: number; intensity: number }`
- `Score`: `{ bpm: number; time_signature: [number, number]; tracks: Track[] }`
- `Note`: `{ pitch: number; duration: number; velocity: number; start: number }`
- `Params`: 部分或全部默认参数键，用于覆盖

### 示例

```ts
import { trajectoryToScore } from "musician-ts-lib";

const trajectory = [
  { velocity: 0.3, direction: 0, intensity: 0.5 },
  { velocity: 0.8, direction: 90, intensity: 0.9 },
  // ...
];
const score = trajectoryToScore(trajectory, { MELODY_KEY_LENGTH: 5 });
// score.tracks[0].notes 为动机轨，可再交给播放或 MIDI 导出
```

