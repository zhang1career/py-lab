"""
将「运动轨迹 + 可调参数 → 乐谱」导出为 TypeScript 库（适配 React Native）。
点击控制面板「导出 TS 库」时调用，生成可独立使用的 TS 包。
"""
import os
from typing import Any

# 默认导出目录（相对于项目根）
DEFAULT_OUT_DIR = "musician-ts-lib"


def _defaults_dict() -> dict[str, Any]:
    """与 conf.py 同步的默认值，用于生成 TS defaults 及文档。"""
    from musician import conf
    return {
        "KEY_ROOT_MIDI": conf.KEY_ROOT_MIDI,
        "KEY_MODE": conf.KEY_MODE,
        "COMPOSE_ARPEGGIO_NOTE_DURATION": conf.COMPOSE_ARPEGGIO_NOTE_DURATION,
        "COMPOSE_COUNTERPOINT_VELOCITY_RATIO": conf.COMPOSE_COUNTERPOINT_VELOCITY_RATIO,
        "MOTIVE_ROOT_MIDI": conf.MOTIVE_ROOT_MIDI,
        "MOTIVE_PITCH_RANGE": conf.MOTIVE_PITCH_RANGE,
        "MOTIVE_TARGET_LENGTH": conf.MOTIVE_TARGET_LENGTH,
        "MOTIVE_BASE_DURATION": conf.MOTIVE_BASE_DURATION,
        "MOTIVE_MIN_VELOCITY": conf.MOTIVE_MIN_VELOCITY,
        "MOTIVE_MAX_VELOCITY": conf.MOTIVE_MAX_VELOCITY,
        "MOTIVE_STYLE": conf.MOTIVE_STYLE,
        "TRAJ_WEIGHT_VELOCITY_OFFSET": conf.TRAJ_WEIGHT_VELOCITY_OFFSET,
        "TRAJ_WEIGHT_FLOOR": conf.TRAJ_WEIGHT_FLOOR,
        "TRAJ_WEIGHT_DIR_CHANGE": conf.TRAJ_WEIGHT_DIR_CHANGE,
        "TRAJ_WARP_ALPHA_LO": conf.TRAJ_WARP_ALPHA_LO,
        "TRAJ_WARP_ALPHA_SPAN": conf.TRAJ_WARP_ALPHA_SPAN,
        "TRAJ_RADIUS_DIVISOR": conf.TRAJ_RADIUS_DIVISOR,
        "TRAJ_JITTER_SCALE_FACTOR": conf.TRAJ_JITTER_SCALE_FACTOR,
        "TRAJ_SHUFFLE_READ_ORDER": conf.TRAJ_SHUFFLE_READ_ORDER,
        "TRAJ_PITCH_NOISE_SEMITONES": conf.TRAJ_PITCH_NOISE_SEMITONES,
        "TRAJ_INVERSE_CDF_MID": conf.TRAJ_INVERSE_CDF_MID,
        "TRAJ_AGGREGATE_DIR_NOISE": conf.TRAJ_AGGREGATE_DIR_NOISE,
        "TRAJ_AGGREGATE_VEL_NOISE": conf.TRAJ_AGGREGATE_VEL_NOISE,
        "TRAJ_AGGREGATE_INT_NOISE": conf.TRAJ_AGGREGATE_INT_NOISE,
        "TRAJ_CONTOUR_RANDOM_SCALE": conf.TRAJ_CONTOUR_RANDOM_SCALE,
        "TRAJ_CONTOUR_DIR_WEIGHT": conf.TRAJ_CONTOUR_DIR_WEIGHT,
        "TRAJ_SINGLE_STEP_NOISE": conf.TRAJ_SINGLE_STEP_NOISE,
        "TRAJ_SINGLE_DIR_WEIGHT": conf.TRAJ_SINGLE_DIR_WEIGHT,
        "TRAJ_SINGLE_VEL_NOISE": conf.TRAJ_SINGLE_VEL_NOISE,
        "TRAJ_SINGLE_INT_NOISE": conf.TRAJ_SINGLE_INT_NOISE,
        "TRAJ_VEL_TO_DUR_OFFSET": conf.TRAJ_VEL_TO_DUR_OFFSET,
        "COMPOSE_DEFAULT_BPM": conf.COMPOSE_DEFAULT_BPM,
        "COMPOSE_ACCOMPANIMENT_VELOCITY": conf.COMPOSE_ACCOMPANIMENT_VELOCITY,
        "COMPOSE_CHORD_DURATION": conf.COMPOSE_CHORD_DURATION,
        "COMPOSE_ACCOMPANIMENT_STYLE": conf.COMPOSE_ACCOMPANIMENT_STYLE,
        "COMPOSE_ADD_COUNTERPOINT": conf.COMPOSE_ADD_COUNTERPOINT,
        "COMPOSE_COUNTERPOINT_STYLE": conf.COMPOSE_COUNTERPOINT_STYLE,
        "TIME_SIGNATURE_NUMERATOR": conf.TIME_SIGNATURE_NUMERATOR,
        "TIME_SIGNATURE_DENOMINATOR": conf.TIME_SIGNATURE_DENOMINATOR,
        "BEATS_PER_BAR": conf.BEATS_PER_BAR,
        "GROOVE_ACCENT_STRONG_BEAT_FACTOR": conf.GROOVE_ACCENT_STRONG_BEAT_FACTOR,
        "GROOVE_SWING_AMOUNT": conf.GROOVE_SWING_AMOUNT,
    }


def _ts_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return str(v)
    if isinstance(v, str):
        return repr(v)
    return repr(v)


def _generate_defaults_ts(defaults: dict[str, Any]) -> str:
    lines = [
        "/** Default parameters (same names as Python conf); override via trajectoryToScore(trajectory, params). */",
        "export const DEFAULT_PARAMS = {",
    ]
    for k, val in defaults.items():
        lines.append(f"  {k}: {_ts_value(val)},")
    lines.append("} as const;")
    lines.append("")
    lines.append("export type Params = { [K in keyof typeof DEFAULT_PARAMS]?: typeof DEFAULT_PARAMS[K] };")
    return "\n".join(lines)


def export_ts_lib(out_dir: str | None = None) -> str:
    """
    生成 TypeScript 库到 out_dir（默认项目根下的 musician-ts-lib）。
    返回写入的绝对路径。
    """
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    target = os.path.join(root, out_dir or DEFAULT_OUT_DIR)
    os.makedirs(target, exist_ok=True)
    src = os.path.join(target, "src")
    os.makedirs(src, exist_ok=True)

    defaults = _defaults_dict()
    defaults_ts = _generate_defaults_ts(defaults)

    # ---------- types.ts ----------
    types_ts = r'''/**
 * Data types for trajectory → score pipeline (mirrors Python musician.models).
 */

export interface TrajectoryPoint {
  velocity: number;   // 0~1
  direction: number;  // e.g. angle 0~360
  intensity: number; // 0~1
}

export interface Note {
  pitch: number;    // MIDI 0-127
  duration: number; // beats
  velocity: number; // 0~1
  start: number;    // beats
}

export interface Track {
  name: string;
  notes: Note[];
}

export interface Score {
  bpm: number;
  time_signature: [number, number];
  tracks: Track[];
}
'''

    # ---------- tonality.ts ----------
    tonality_ts = r'''/**
 * Tonality: scale, scale snap, I-IV-V-I chords (port from musician.tonality).
 */

const MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11];
const NATURAL_MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10];
const PROGRESSION_DEGREES = [0, 3, 4, 0]; // I-IV-V-I

export function getScale(mode: string): number[] {
  return mode === "minor" ? [...NATURAL_MINOR_SCALE] : [...MAJOR_SCALE];
}

function scaleDegreeToSemitone(degree: number, mode: string): number {
  const scale = getScale(mode);
  const octaves = Math.floor(degree / 7);
  const idx = ((degree % 7) + 7) % 7;
  return octaves * 12 + scale[idx];
}

function getTriadSemitones(degreeIndex: number, mode: string): [number, number, number] {
  const root = scaleDegreeToSemitone(degreeIndex, mode);
  if (mode === "minor") {
    return [root, root + 3, root + 7];
  }
  return [root, root + 4, root + 7];
}

export function getProgressionChords(rootMidi: number, mode: string): number[][] {
  const chords: number[][] = [];
  for (const deg of PROGRESSION_DEGREES) {
    const [r, t, f] = getTriadSemitones(deg, mode);
    chords.push([rootMidi + r, rootMidi + t, rootMidi + f]);
  }
  return chords;
}

function getScaleMidiSet(rootMidi: number, mode: string, octaves: number = 3): Set<number> {
  const scale = getScale(mode);
  const out = new Set<number>();
  for (let o = -octaves; o <= octaves; o++) {
    for (const s of scale) {
      const p = rootMidi + o * 12 + s;
      if (p >= 0 && p <= 127) out.add(p);
    }
  }
  return out;
}

export function snapPitchToScale(pitch: number, rootMidi: number, mode: string): number {
  const scaleSet = getScaleMidiSet(rootMidi, mode);
  if (scaleSet.has(pitch)) return pitch;
  for (let d = 1; d < 12; d++) {
    if (pitch + d <= 127 && scaleSet.has(pitch + d)) return pitch + d;
    if (pitch - d >= 0 && scaleSet.has(pitch - d)) return pitch - d;
  }
  return Math.max(0, Math.min(127, pitch));
}

export function intervalInScaleSteps(rootMidi: number, mode: string, fromPitch: number, steps: number): number {
  const scale = getScale(mode);
  const base = snapPitchToScale(fromPitch, rootMidi, mode);
  const relSemitone = ((base - rootMidi) % 12 + 12) % 12;
  let degreeInOctave = 0;
  for (let i = 0; i < scale.length; i++) {
    const s = scale[i];
    if (s !== undefined && (((relSemitone - s) % 12) + 12) % 12 === 0) {
      degreeInOctave = i;
      break;
    }
  }
  let octaveOffset = Math.floor((base - rootMidi) / 12);
  if (base - rootMidi < 0 && (base - rootMidi) % 12 !== 0) octaveOffset -= 1;
  let totalDegrees = octaveOffset * 7 + degreeInOctave + steps;
  let newOct = Math.floor(totalDegrees / 7);
  let newIdx = totalDegrees % 7;
  if (newIdx < 0) {
    newIdx += 7;
    newOct -= 1;
  }
  const semitone = newOct * 12 + (scale[newIdx] ?? 0);
  return Math.max(0, Math.min(127, rootMidi + semitone));
}
'''

    # ---------- rng.ts (seeded) ----------
    rng_ts = r'''/**
 * Seeded RNG (mulberry32) for reproducible motive from same trajectory + seed.
 */

export function createRng(seed: number): () => number {
  return function next() {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function shuffle<T>(arr: T[], random: () => number): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}
'''

    # ---------- trajectoryToMotive.ts ----------
    trajectory_to_motive_ts = r'''/**
 * Map motion trajectory to motive (melody contour, rhythm, velocity). Port from musician.trajectory_to_motive.
 */

import type { TrajectoryPoint, Note } from "./types";
import type { Params } from "./defaults";
import { DEFAULT_PARAMS } from "./defaults";
import { snapPitchToScale } from "./tonality";
import { createRng, shuffle } from "./rng";

function getP<T>(p: Params, key: keyof typeof DEFAULT_PARAMS, fallback: T): T {
  const v = p[key];
  return (v !== undefined && v !== null) ? (v as T) : fallback;
}

function normalizeDirection(d: number): number {
  while (d > 360) d -= 360;
  while (d < 0) d += 360;
  return (d / 360) * 2 - 1;
}

function contentWeights(trajectory: TrajectoryPoint[], p: Params): number[] {
  const weights: number[] = [];
  const wvo = getP(p, "TRAJ_WEIGHT_VELOCITY_OFFSET", DEFAULT_PARAMS.TRAJ_WEIGHT_VELOCITY_OFFSET) as number;
  const wf = getP(p, "TRAJ_WEIGHT_FLOOR", DEFAULT_PARAMS.TRAJ_WEIGHT_FLOOR) as number;
  const wdc = getP(p, "TRAJ_WEIGHT_DIR_CHANGE", DEFAULT_PARAMS.TRAJ_WEIGHT_DIR_CHANGE) as number;
  let prevDir = normalizeDirection(trajectory[0].direction);
  for (let i = 0; i < trajectory.length; i++) {
    const pt = trajectory[i];
    const d = normalizeDirection(pt.direction);
    const change = i > 0 ? Math.abs(d - prevDir) : 0;
    prevDir = d;
    const w = pt.intensity * (wvo + Math.max(0, Math.min(1, pt.velocity))) + wf + wdc * change;
    weights.push(w);
  }
  return weights;
}

function weightsToCdf(weights: number[]): number[] {
  const total = weights.reduce((a, b) => a + b, 0);
  if (total <= 0) {
    return weights.map((_, i) => i / Math.max(1, weights.length - 1));
  }
  const cdf = [0];
  for (const w of weights) {
    cdf.push(cdf[cdf.length - 1]! + w / total);
  }
  return cdf;
}

function warpAlpha(trajectory: TrajectoryPoint[], p: Params): number {
  const meanVel = trajectory.reduce((s, pt) => s + Math.max(0, Math.min(1, pt.velocity)), 0) / trajectory.length;
  const lo = getP(p, "TRAJ_WARP_ALPHA_LO", DEFAULT_PARAMS.TRAJ_WARP_ALPHA_LO) as number;
  const span = getP(p, "TRAJ_WARP_ALPHA_SPAN", DEFAULT_PARAMS.TRAJ_WARP_ALPHA_SPAN) as number;
  return lo + span * meanVel;
}

function inverseCdf(cdf: number[], t: number): number {
  t = Math.max(0, Math.min(1, t));
  const n = cdf.length - 1;
  if (n <= 0) return 0;
  for (let i = 0; i < n; i++) {
    if (cdf[i]! <= t && t <= cdf[i + 1]!) {
      if (cdf[i + 1] === cdf[i]) return i;
      const frac = (t - cdf[i]!) / (cdf[i + 1]! - cdf[i]!);
      return i + frac;
    }
  }
  return n;
}

function warpToPositions(cdf: number[], targetLength: number, alpha: number, p: Params): number[] {
  if (targetLength <= 0) return [];
  const mid = getP(p, "TRAJ_INVERSE_CDF_MID", DEFAULT_PARAMS.TRAJ_INVERSE_CDF_MID) as number;
  if (targetLength === 1) return [inverseCdf(cdf, mid)];
  const positions: number[] = [];
  for (let k = 0; k < targetLength; k++) {
    const u = k / (targetLength - 1);
    const t = Math.pow(u, alpha);
    positions.push(inverseCdf(cdf, t));
  }
  return positions;
}

function jitterPositions(positions: number[], trajectoryLen: number, rng: () => number, p: Params): number[] {
  const jitterScale = Math.max(1, trajectoryLen * (getP(p, "TRAJ_JITTER_SCALE_FACTOR", DEFAULT_PARAMS.TRAJ_JITTER_SCALE_FACTOR) as number));
  return positions.map(pos =>
    Math.max(0, Math.min(trajectoryLen - 1, pos + (rng() - 0.5) * jitterScale))
  );
}

function aggregateAtPosition(
  trajectory: TrajectoryPoint[],
  pos: number,
  radius: number,
  rng: () => number,
  p: Params,
  noiseScale: number
): [number, number, number] {
  const n = trajectory.length;
  const idxLo = Math.max(0, Math.floor(pos) - radius);
  const idxHi = Math.min(n - 1, Math.floor(pos) + radius);
  let sumD = 0, sumV = 0, sumI = 0, sumW = 0;
  for (let i = idxLo; i <= idxHi; i++) {
    const dist = Math.abs(i - pos);
    const w = Math.max(0, 1 - dist / (radius + 1));
    const pt = trajectory[i]!;
    sumD += normalizeDirection(pt.direction) * w;
    sumV += Math.max(0, Math.min(1, pt.velocity)) * w;
    sumI += Math.max(0, Math.min(1, pt.intensity)) * w;
    sumW += w;
  }
  const nd = (getP(p, "TRAJ_AGGREGATE_DIR_NOISE", DEFAULT_PARAMS.TRAJ_AGGREGATE_DIR_NOISE) as number) * noiseScale;
  const nv = (getP(p, "TRAJ_AGGREGATE_VEL_NOISE", DEFAULT_PARAMS.TRAJ_AGGREGATE_VEL_NOISE) as number) * noiseScale;
  const ni = (getP(p, "TRAJ_AGGREGATE_INT_NOISE", DEFAULT_PARAMS.TRAJ_AGGREGATE_INT_NOISE) as number) * noiseScale;
  if (sumW <= 0) {
    const pt = trajectory[Math.min(Math.floor(pos), n - 1)]!;
    return [
      normalizeDirection(pt.direction) + (rng() - 0.5) * nd,
      Math.max(0, Math.min(1, Math.max(0, Math.min(1, pt.velocity)) + (rng() - 0.5) * nv)),
      Math.max(0, Math.min(1, Math.max(0, Math.min(1, pt.intensity)) + (rng() - 0.5) * ni)),
    ];
  }
  let d = sumD / sumW + (rng() - 0.5) * nd;
  let v = Math.max(0, Math.min(1, sumV / sumW + (rng() - 0.5) * nv));
  let i = Math.max(0, Math.min(1, sumI / sumW + (rng() - 0.5) * ni));
  return [d, v, i];
}

function contourWithNoise(
  normalizedDirs: number[],
  pitchRange: number,
  rng: () => number,
  p: Params,
  randomScale?: number,
  dirWeight?: number
): number[] {
  const rs = randomScale ?? (getP(p, "TRAJ_CONTOUR_RANDOM_SCALE", DEFAULT_PARAMS.TRAJ_CONTOUR_RANDOM_SCALE) as number);
  const dw = dirWeight ?? (getP(p, "TRAJ_CONTOUR_DIR_WEIGHT", DEFAULT_PARAMS.TRAJ_CONTOUR_DIR_WEIGHT) as number);
  const offsets: number[] = [];
  let cum = 0;
  for (const d of normalizedDirs) {
    const step = (rng() - 0.5) * rs + d * dw;
    cum += step;
    cum = Math.max(-pitchRange, Math.min(pitchRange, cum));
    offsets.push(Math.round(cum));
  }
  return offsets;
}

function velocityToDuration(velocity: number, baseDuration: number, p: Params): number {
  const v = Math.max(0, Math.min(1, velocity));
  const offset = getP(p, "TRAJ_VEL_TO_DUR_OFFSET", DEFAULT_PARAMS.TRAJ_VEL_TO_DUR_OFFSET) as number;
  return baseDuration * (offset - v);
}

function singlePointMotive(
  point: TrajectoryPoint,
  targetLength: number,
  rng: () => number,
  rootMidi: number,
  pitchRange: number,
  baseDuration: number,
  minVel: number,
  maxVel: number,
  keyRoot: number,
  keyMode: string,
  p: Params
): Note[] {
  const d0 = normalizeDirection(point.direction);
  const v0 = Math.max(0, Math.min(1, point.velocity));
  const i0 = Math.max(0, Math.min(1, point.intensity));
  const stepNoise = getP(p, "TRAJ_SINGLE_STEP_NOISE", DEFAULT_PARAMS.TRAJ_SINGLE_STEP_NOISE) as number;
  const dirWeight = getP(p, "TRAJ_SINGLE_DIR_WEIGHT", DEFAULT_PARAMS.TRAJ_SINGLE_DIR_WEIGHT) as number;
  const velNoise = getP(p, "TRAJ_SINGLE_VEL_NOISE", DEFAULT_PARAMS.TRAJ_SINGLE_VEL_NOISE) as number;
  const intNoise = getP(p, "TRAJ_SINGLE_INT_NOISE", DEFAULT_PARAMS.TRAJ_SINGLE_INT_NOISE) as number;
  const motive: Note[] = [];
  let cum = 0;
  let t = 0;
  for (let i = 0; i < targetLength; i++) {
    cum += d0 * dirWeight + (rng() - 0.5) * stepNoise;
    cum = Math.max(-pitchRange, Math.min(pitchRange, cum));
    const v = Math.max(0, Math.min(1, v0 + (rng() - 0.5) * velNoise));
    const inten = Math.max(0, Math.min(1, i0 + (rng() - 0.5) * intNoise));
    const dur = velocityToDuration(v, baseDuration, p);
    const vel = Math.max(0, Math.min(1, minVel + inten * (maxVel - minVel)));
    const pitch = snapPitchToScale(Math.round(rootMidi + cum), keyRoot, keyMode);
    motive.push({ pitch, duration: dur, velocity: vel, start: t });
    t += dur;
  }
  return motive;
}

export function trajectoryToMotive(
  trajectory: TrajectoryPoint[],
  params: Params = {},
  seed?: number
): Note[] {
  if (trajectory.length === 0) return [];
  const p = { ...DEFAULT_PARAMS, ...params };
  const targetLength = getP(p, "MOTIVE_TARGET_LENGTH", DEFAULT_PARAMS.MOTIVE_TARGET_LENGTH) as number;
  const rootMidi = getP(p, "MOTIVE_ROOT_MIDI", DEFAULT_PARAMS.MOTIVE_ROOT_MIDI) as number;
  const pitchRange = getP(p, "MOTIVE_PITCH_RANGE", DEFAULT_PARAMS.MOTIVE_PITCH_RANGE) as number;
  const baseDuration = getP(p, "MOTIVE_BASE_DURATION", DEFAULT_PARAMS.MOTIVE_BASE_DURATION) as number;
  const minVel = getP(p, "MOTIVE_MIN_VELOCITY", DEFAULT_PARAMS.MOTIVE_MIN_VELOCITY) as number;
  const maxVel = getP(p, "MOTIVE_MAX_VELOCITY", DEFAULT_PARAMS.MOTIVE_MAX_VELOCITY) as number;
  const keyRoot = getP(p, "KEY_ROOT_MIDI", DEFAULT_PARAMS.KEY_ROOT_MIDI) as number;
  const keyMode = getP(p, "KEY_MODE", DEFAULT_PARAMS.KEY_MODE) as string;
  const style = (getP(p, "MOTIVE_STYLE", DEFAULT_PARAMS.MOTIVE_STYLE) as string).toLowerCase();
  const rng = createRng(seed ?? 0);

  if (trajectory.length === 1) {
    return singlePointMotive(
      trajectory[0]!, targetLength, rng, rootMidi, pitchRange, baseDuration, minVel, maxVel, keyRoot, keyMode, p
    );
  }

  let tl: number = targetLength;
  let pr: number = pitchRange;
  let bd: number = baseDuration;
  let shuffleRead: boolean = getP(p, "TRAJ_SHUFFLE_READ_ORDER", DEFAULT_PARAMS.TRAJ_SHUFFLE_READ_ORDER) as boolean;
  let contourRandomScale: number = getP(p, "TRAJ_CONTOUR_RANDOM_SCALE", DEFAULT_PARAMS.TRAJ_CONTOUR_RANDOM_SCALE) as number;
  let contourDirWeight: number = getP(p, "TRAJ_CONTOUR_DIR_WEIGHT", DEFAULT_PARAMS.TRAJ_CONTOUR_DIR_WEIGHT) as number;
  let pitchNoise: number = getP(p, "TRAJ_PITCH_NOISE_SEMITONES", DEFAULT_PARAMS.TRAJ_PITCH_NOISE_SEMITONES) as number;
  let aggNoiseScale: number = 1;
  if (style === "lyrical") {
    tl = Math.min(targetLength, 96);
    pr = Math.min(pitchRange, 10);
    bd = baseDuration * 1.4;
    shuffleRead = false;
    contourRandomScale = 2;
    contourDirWeight = 1.2;
    pitchNoise = 1;
    aggNoiseScale = 0.4;
  } else if (style === "minimal") {
    tl = Math.max(8, Math.floor(targetLength / 2));
    pr = Math.min(pitchRange, 8);
    bd = baseDuration * 1.2;
    shuffleRead = false;
    contourRandomScale = 1.5;
    contourDirWeight = 0.6;
    pitchNoise = 0;
    aggNoiseScale = 0.3;
  }

  const n = trajectory.length;
  const weights = contentWeights(trajectory, p);
  const cdf = weightsToCdf(weights);
  const alpha = warpAlpha(trajectory, p);
  let trajectoryPositions = warpToPositions(cdf, tl, alpha, p);
  trajectoryPositions = jitterPositions(trajectoryPositions, n, rng, p);
  if (shuffleRead) {
    const perm = shuffle(Array.from({ length: tl }, (_, j) => j), rng);
    trajectoryPositions = perm.map((j) => trajectoryPositions[j]!);
  }

  const radius = Math.max(1, Math.floor(n / (getP(p, "TRAJ_RADIUS_DIVISOR", DEFAULT_PARAMS.TRAJ_RADIUS_DIVISOR) as number)));
  const dirs: number[] = [];
  const vels: number[] = [];
  const ints: number[] = [];
  for (const pos of trajectoryPositions) {
    const [d, v, i] = aggregateAtPosition(trajectory, pos, radius, rng, p, aggNoiseScale);
    dirs.push(d);
    vels.push(v);
    ints.push(i);
  }

  let pitchOffsets = contourWithNoise(dirs, pr, rng, p, contourRandomScale, contourDirWeight);
  for (let k = 0; k < tl; k++) {
    const no = Math.floor(rng() * (2 * pitchNoise + 1)) - pitchNoise;
    pitchOffsets[k] = (pitchOffsets[k] ?? 0) + no;
  }

  const motive: Note[] = [];
  let t = 0;
  for (let k = 0; k < tl; k++) {
    const dur = velocityToDuration(vels[k]!, bd, p);
    const vel = Math.max(0, Math.min(1, minVel + (ints[k] ?? 0) * (maxVel - minVel)));
    let pitch = Math.max(0, Math.min(127, rootMidi + (pitchOffsets[k] ?? 0)));
    pitch = snapPitchToScale(pitch, keyRoot, keyMode);
    motive.push({ pitch, duration: dur, velocity: vel, start: t });
    t += dur;
  }
  return motive;
}
'''

    # ---------- composer.ts ----------
    composer_ts = r'''/**
 * Compose: motive + accompaniment + optional counterpoint → Score. Port from musician.composer.
 */

import type { Note, Score, Track } from "./types";
import type { Params } from "./defaults";
import { DEFAULT_PARAMS } from "./defaults";
import { getProgressionChords, intervalInScaleSteps, getScale } from "./tonality";

function getP<T>(p: Params, key: keyof typeof DEFAULT_PARAMS, fallback: T): T {
  const v = p[key];
  return (v !== undefined && v !== null) ? (v as T) : fallback;
}

function accompBlock(chords: number[][], endTime: number, chordDuration: number, velocity: number): Note[] {
  const notes: Note[] = [];
  let t = 0;
  let i = 0;
  while (t < endTime) {
    for (const pitch of chords[i % chords.length]!) {
      notes.push({ pitch, duration: chordDuration, velocity, start: t });
    }
    t += chordDuration;
    i++;
  }
  return notes;
}

function accompArpeggiated(
  chords: number[][],
  endTime: number,
  chordDuration: number,
  noteDur: number,
  velocity: number
): Note[] {
  const notes: Note[] = [];
  let t = 0;
  let i = 0;
  while (t < endTime) {
    const triad = chords[i % chords.length]!;
    for (let j = 0; j < triad.length; j++) {
      notes.push({ pitch: triad[j]!, duration: noteDur, velocity, start: t + j * noteDur });
    }
    t += chordDuration;
    i++;
  }
  return notes;
}

function accompRhythmPattern(
  chords: number[][],
  endTime: number,
  chordDuration: number,
  velocity: number
): Note[] {
  const notes: Note[] = [];
  let t = 0;
  let i = 0;
  while (t < endTime) {
    const triad = chords[i % chords.length]!;
    const [root, third, fifth] = [triad[0]!, triad[1]!, triad[2]!];
    const half = chordDuration / 2;
    notes.push({ pitch: root, duration: half, velocity, start: t });
    notes.push({ pitch: third, duration: half, velocity: velocity * 0.9, start: t + half });
    notes.push({ pitch: fifth, duration: half, velocity: velocity * 0.9, start: t + half });
    t += chordDuration;
    i++;
  }
  return notes;
}

function counterpointParallel(
  motive: Note[],
  rootMidi: number,
  mode: string,
  steps: number,
  velocityRatio: number
): Note[] {
  const notes: Note[] = [];
  for (const n of motive) {
    const pitch = intervalInScaleSteps(rootMidi, mode, n.pitch, steps);
    const vel = Math.max(0, Math.min(1, n.velocity * velocityRatio));
    notes.push({ pitch, duration: n.duration, velocity: vel, start: n.start });
  }
  return notes;
}

function counterpointOstinato(
  motive: Note[],
  rootMidi: number,
  mode: string,
  velocityRatio: number
): Note[] {
  const scale = getScale(mode);
  const ostinatoSemitones = [scale[4]!, scale[2]!, scale[0]!, scale[2]!];
  const noteDur = 0.5;
  const notes: Note[] = [];
  const endTime = motive.length ? Math.max(...motive.map((n) => n.start + n.duration)) : 0;
  let t = 0;
  let idx = 0;
  while (t < endTime) {
    const sem = ostinatoSemitones[idx % 4]!;
    let pitch = rootMidi + 12 + sem;
    if (pitch > 127) pitch -= 12;
    notes.push({ pitch, duration: noteDur, velocity: velocityRatio, start: t });
    t += noteDur;
    idx++;
  }
  return notes;
}

export function compose(motive: Note[], params: Params = {}): Score {
  const p = { ...DEFAULT_PARAMS, ...params };
  const keyRoot = getP(p, "KEY_ROOT_MIDI", DEFAULT_PARAMS.KEY_ROOT_MIDI) as number;
  const keyMode = getP(p, "KEY_MODE", DEFAULT_PARAMS.KEY_MODE) as string;
  const bpm = getP(p, "COMPOSE_DEFAULT_BPM", DEFAULT_PARAMS.COMPOSE_DEFAULT_BPM) as number;
  const accompVel = getP(p, "COMPOSE_ACCOMPANIMENT_VELOCITY", DEFAULT_PARAMS.COMPOSE_ACCOMPANIMENT_VELOCITY) as number;
  const accompStyle = getP(p, "COMPOSE_ACCOMPANIMENT_STYLE", DEFAULT_PARAMS.COMPOSE_ACCOMPANIMENT_STYLE) as string;
  const addCounterpoint = getP(p, "COMPOSE_ADD_COUNTERPOINT", DEFAULT_PARAMS.COMPOSE_ADD_COUNTERPOINT) as boolean;
  const counterpointStyle = getP(p, "COMPOSE_COUNTERPOINT_STYLE", DEFAULT_PARAMS.COMPOSE_COUNTERPOINT_STYLE) as string;
  const chordDuration = getP(p, "COMPOSE_CHORD_DURATION", DEFAULT_PARAMS.COMPOSE_CHORD_DURATION) as number;
  const arpNoteDur = getP(p, "COMPOSE_ARPEGGIO_NOTE_DURATION", DEFAULT_PARAMS.COMPOSE_ARPEGGIO_NOTE_DURATION) as number;
  const cptVelRatio = getP(p, "COMPOSE_COUNTERPOINT_VELOCITY_RATIO", DEFAULT_PARAMS.COMPOSE_COUNTERPOINT_VELOCITY_RATIO) as number;
  const num = getP(p, "TIME_SIGNATURE_NUMERATOR", DEFAULT_PARAMS.TIME_SIGNATURE_NUMERATOR) as number;
  const denom = getP(p, "TIME_SIGNATURE_DENOMINATOR", DEFAULT_PARAMS.TIME_SIGNATURE_DENOMINATOR) as number;

  const chords = getProgressionChords(keyRoot, keyMode);
  const tracks: Track[] = [];
  const motiveNotes = motive.map((n) => ({ ...n }));
  tracks.push({ name: "motive", notes: motiveNotes });

  if (motive.length > 0) {
    const endTime = Math.max(...motive.map((n) => n.start + n.duration));
    let accomp: Note[];
    if (accompStyle === "arpeggiated") {
      accomp = accompArpeggiated(chords, endTime, chordDuration, arpNoteDur, accompVel);
    } else if (accompStyle === "rhythm_pattern") {
      accomp = accompRhythmPattern(chords, endTime, chordDuration, accompVel);
    } else {
      accomp = accompBlock(chords, endTime, chordDuration, accompVel);
    }
    tracks.push({ name: "accompaniment", notes: accomp });
  }

  if (addCounterpoint && motive.length > 0) {
    let cpt: Note[];
    if (counterpointStyle === "parallel_6th") {
      cpt = counterpointParallel(motive, keyRoot, keyMode, 5, cptVelRatio);
    } else if (counterpointStyle === "ostinato") {
      cpt = counterpointOstinato(motive, keyRoot, keyMode, cptVelRatio);
    } else {
      cpt = counterpointParallel(motive, keyRoot, keyMode, 2, cptVelRatio);
    }
    tracks.push({ name: "counterpoint", notes: cpt });
  }

  const score: Score = { bpm, time_signature: [num, denom], tracks };
  return applyGroove(score, p);
}

function applyGroove(score: Score, p: Params): Score {
  const beatsPerBar = getP(p, "BEATS_PER_BAR", DEFAULT_PARAMS.BEATS_PER_BAR) as number;
  const accentFactor = getP(p, "GROOVE_ACCENT_STRONG_BEAT_FACTOR", DEFAULT_PARAMS.GROOVE_ACCENT_STRONG_BEAT_FACTOR) as number;
  const swingAmount = getP(p, "GROOVE_SWING_AMOUNT", DEFAULT_PARAMS.GROOVE_SWING_AMOUNT) as number;
  const accentTolerance = 0.05;
  const newTracks: Track[] = [];
  for (const track of score.tracks) {
    const newNotes: Note[] = [];
    for (const n of track.notes) {
      let vel = n.velocity;
      let start = n.start;
      const barPos = start % beatsPerBar;
      if (barPos < accentTolerance) vel = Math.min(1, vel * accentFactor);
      const halfBeatIndex = Math.round(start * 2);
      if (halfBeatIndex % 2 === 1) start = start + swingAmount * 0.5;
      newNotes.push({ ...n, velocity: vel, start });
    }
    newTracks.push({ name: track.name, notes: newNotes });
  }
  return { ...score, tracks: newTracks };
}
'''

    # ---------- index.ts ----------
    index_ts = r'''/**
 * Musician Score Library (React Native friendly).
 * Input: motion trajectory + optional params (same names as Python conf, override defaults).
 * Output: Score (bpm, time_signature, tracks with notes: pitch, duration, velocity, start).
 *
 * Usage:
 *   import { trajectoryToScore } from "musician-ts-lib";
 *   const trajectory = [{ velocity: 0.5, direction: 180, intensity: 0.7 }, ...];
 *   const score = trajectoryToScore(trajectory, { MOTIVE_TARGET_LENGTH: 32 }, 12345);
 */

import type { TrajectoryPoint, Score } from "./types";
import type { Params } from "./defaults";
import { trajectoryToMotive } from "./trajectoryToMotive";
import { compose } from "./composer";

export type { TrajectoryPoint, Note, Track, Score } from "./types";
export type { Params } from "./defaults";
export { DEFAULT_PARAMS } from "./defaults";

/**
 * Generate a Score from motion trajectory and optional parameters.
 * Same-name keys in params override defaults. seed is optional for reproducible motive.
 */
export function trajectoryToScore(
  trajectory: TrajectoryPoint[],
  params: Params = {},
  seed?: number
): Score {
  const motive = trajectoryToMotive(trajectory, params, seed);
  return compose(motive, params);
}

export { trajectoryToMotive } from "./trajectoryToMotive";
export { compose } from "./composer";
'''

    # ---------- package.json ----------
    package_json = '''{
  "name": "musician-ts-lib",
  "version": "1.0.0",
  "description": "Trajectory to score: motion + params → Score (React Native friendly)",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "prepublishOnly": "npm run build"
  },
  "keywords": ["music", "score", "trajectory", "react-native"],
  "author": "",
  "license": "MIT",
  "devDependencies": {
    "typescript": "^5.0.0"
  },
  "files": ["dist", "src"]
}
'''

    # ---------- tsconfig.json ----------
    tsconfig_json = '''{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "declaration": true,
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*.ts"],
  "exclude": ["node_modules", "dist"]
}
'''

    # ---------- README ----------
    readme = r'''# musician-ts-lib

由运动轨迹与可调参数生成乐谱的 TypeScript 库，适配 React Native（无 Node 专有 API）。

## 安装

```bash
npm install
npm run build
```

或在 monorepo 中直接引用 `src/` 下的 TypeScript 源码。

## API

### `trajectoryToScore(trajectory, params?, seed?)`

- **trajectory**: `TrajectoryPoint[]` — 运动轨迹，每点 `{ velocity, direction, intensity }`（velocity/intensity 建议 0~1，direction 如 0~360 角度）
- **params**: `Params`（可选）— 与 Python `conf` 同名的键，用于覆盖默认值，如 `{ MOTIVE_TARGET_LENGTH: 32, KEY_MODE: "minor" }`
- **seed**: `number`（可选）— 随机种子，相同轨迹+种子得到相同动机
- **返回**: `Score` — `{ bpm, time_signature, tracks: { name, notes: { pitch, duration, velocity, start }[] }[] }`

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
const score = trajectoryToScore(trajectory, { MOTIVE_TARGET_LENGTH: 64 }, 42);
// score.tracks[0].notes 为动机轨，可再交给播放或 MIDI 导出
```

'''

    files = [
        (os.path.join(src, "types.ts"), types_ts),
        (os.path.join(src, "defaults.ts"), defaults_ts),
        (os.path.join(src, "tonality.ts"), tonality_ts),
        (os.path.join(src, "rng.ts"), rng_ts),
        (os.path.join(src, "trajectoryToMotive.ts"), trajectory_to_motive_ts),
        (os.path.join(src, "composer.ts"), composer_ts),
        (os.path.join(src, "index.ts"), index_ts),
        (os.path.join(target, "package.json"), package_json),
        (os.path.join(target, "tsconfig.json"), tsconfig_json),
        (os.path.join(target, "README.md"), readme),
    ]
    for path, content in files:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return os.path.abspath(target)
