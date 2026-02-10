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
        "MELODY_TABLE_PATH": getattr(conf, "MELODY_TABLE_PATH", "") or "",
        "MELODY_KEY": getattr(conf, "MELODY_KEY", "1,3,5,7"),
        "MELODY_KEY_LENGTH": getattr(conf, "MELODY_KEY_LENGTH", 5),
        "MELODY_FALLBACK": getattr(conf, "MELODY_FALLBACK", True),
        "COMPOSE_DEFAULT_BPM": conf.COMPOSE_DEFAULT_BPM,
        "COMPOSE_ADD_ACCOMPANIMENT": getattr(conf, "COMPOSE_ADD_ACCOMPANIMENT", True),
        "COMPOSE_ACCOMPANIMENT_VELOCITY": conf.COMPOSE_ACCOMPANIMENT_VELOCITY,
        "COMPOSE_CHORD_DURATION": conf.COMPOSE_CHORD_DURATION,
        "COMPOSE_ACCOMPANIMENT_STYLE": conf.COMPOSE_ACCOMPANIMENT_STYLE,
        "COMPOSE_ADD_COUNTERPOINT": conf.COMPOSE_ADD_COUNTERPOINT,
        "COMPOSE_COUNTERPOINT_STYLE": conf.COMPOSE_COUNTERPOINT_STYLE,
        "COMPOSE_ADD_PAD": getattr(conf, "COMPOSE_ADD_PAD", False),
        "COMPOSE_PAD_VELOCITY": getattr(conf, "COMPOSE_PAD_VELOCITY", 0.25),
        "COMPOSE_PAD_CHORD_DURATION": getattr(conf, "COMPOSE_PAD_CHORD_DURATION", 4.0),
        "COMPOSE_PAD_OCTAVE_OFFSET": getattr(conf, "COMPOSE_PAD_OCTAVE_OFFSET", 1),
        "COMPOSE_ADD_BASS": getattr(conf, "COMPOSE_ADD_BASS", False),
        "COMPOSE_BASS_VELOCITY": getattr(conf, "COMPOSE_BASS_VELOCITY", 0.4),
        "COMPOSE_BASS_STYLE": getattr(conf, "COMPOSE_BASS_STYLE", "root_only"),
        "COMPOSE_BASS_OCTAVE_OFFSET": getattr(conf, "COMPOSE_BASS_OCTAVE_OFFSET", -1),
        "COMPOSE_ADD_PERCUSSION": getattr(conf, "COMPOSE_ADD_PERCUSSION", False),
        "COMPOSE_PERCUSSION_VELOCITY": getattr(conf, "COMPOSE_PERCUSSION_VELOCITY", 0.5),
        "COMPOSE_PERCUSSION_PATTERN": getattr(conf, "COMPOSE_PERCUSSION_PATTERN", "simple_44"),
        "COMPOSE_PERCUSSION_PLAYBACK": getattr(conf, "COMPOSE_PERCUSSION_PLAYBACK", "gm"),
        "COMPOSE_ADD_ORNAMENTATION": getattr(conf, "COMPOSE_ADD_ORNAMENTATION", False),
        "COMPOSE_ORNAMENT_VELOCITY_RATIO": getattr(conf, "COMPOSE_ORNAMENT_VELOCITY_RATIO", 0.6),
        "COMPOSE_ORNAMENT_DENSITY": getattr(conf, "COMPOSE_ORNAMENT_DENSITY", 0.3),
        "COMPOSE_ORNAMENT_MAX_DURATION": getattr(conf, "COMPOSE_ORNAMENT_MAX_DURATION", 0.25),
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

    # ---------- melodyTable.ts ----------
    melody_table_ts = r'''/**
 * Trajectory → key (scale degrees), melody table lookup, fallback. Port from musician.melody_table.
 * API: trajectoryToKey(trajectory, rootMidi, mode, keyLength?) → number[];
 *      lookupMelody(key, rootMidi, mode, table?, useFallback?) → Note[];
 *      trajectoryOrKeyToMotive(trajectoryOrKey, params) → Note[] (trajectory or key as input).
 *      parseMelodyTableFromJson(jsonString) → MelodyTable (load melody_table.json at runtime).
 * params may include MELODY_TABLE (MelodyTable); when set, used for lookup instead of built-in table.
 */

import type { TrajectoryPoint, Note } from "./types";
import type { Params } from "./defaults";
import { DEFAULT_PARAMS } from "./defaults";
import { getScale } from "./tonality";

function getP<T>(p: Params, key: keyof typeof DEFAULT_PARAMS, fallback: T): T {
  const v = p[key];
  return (v !== undefined && v !== null) ? (v as T) : fallback;
}

function normalizeDirection(d: number): number {
  while (d > 360) d -= 360;
  while (d < 0) d += 360;
  return (d / 360) * 2 - 1;
}

function degreeToPitch(degree: number, rootMidi: number, mode: string): number {
  const scale = getScale(mode);
  const d = (degree - 1) % 7;
  const oct = Math.floor((degree - 1) / 7);
  return Math.max(0, Math.min(127, rootMidi + oct * 12 + (scale[d] ?? 0)));
}

/** Motion trajectory → fixed-length key (scale degrees 1–7). */
export function trajectoryToKey(
  trajectory: TrajectoryPoint[],
  rootMidi: number,
  mode: string,
  keyLength: number = 5
): number[] {
  const keyLen = Math.max(1, Math.min(7, keyLength));
  if (trajectory.length === 0) return Array(keyLen).fill(1);
  const n = trajectory.length;
  if (n === 1) {
    const d = normalizeDirection(trajectory[0].direction);
    const scaleIdx = Math.max(0, Math.min(6, Math.round(3 + d * 3)));
    return Array(keyLen).fill(scaleIdx + 1);
  }
  const scale = getScale(mode);
  const indices = keyLen === 1 ? [0] : Array.from({ length: keyLen }, (_, i) => Math.floor(i * (n - 1) / (keyLen - 1)));
  let cum = 3;
  const degrees: number[] = [];
  for (const idx of indices) {
    const p = trajectory[Math.min(idx, n - 1)]!;
    const d = normalizeDirection(p.direction);
    const weight = 0.5 + 0.5 * Math.max(0, Math.min(1, p.velocity)) * Math.max(0, Math.min(1, p.intensity));
    cum += d * 1.5 * weight;
    cum = Math.max(0, Math.min(6, cum));
    degrees.push((Math.round(cum) % 7) + 1);
  }
  return degrees;
}

export type MelodyTable = Record<string, Array<{ degree: number; duration: number; velocity: number }>>;

const DEFAULT_MELODY_TABLE: MelodyTable = {
  "1": [{ degree: 1, duration: 0.5, velocity: 0.85 }, { degree: 3, duration: 0.5, velocity: 0.8 }, { degree: 5, duration: 0.5, velocity: 0.8 }, { degree: 3, duration: 0.5, velocity: 0.75 }, { degree: 1, duration: 1, velocity: 0.8 }],
  "2": [{ degree: 2, duration: 0.5, velocity: 0.8 }, { degree: 4, duration: 0.5, velocity: 0.8 }, { degree: 5, duration: 0.5, velocity: 0.75 }, { degree: 3, duration: 0.5, velocity: 0.8 }, { degree: 1, duration: 1, velocity: 0.85 }],
  "3": [{ degree: 3, duration: 0.5, velocity: 0.8 }, { degree: 5, duration: 0.5, velocity: 0.8 }, { degree: 3, duration: 0.5, velocity: 0.75 }, { degree: 1, duration: 0.5, velocity: 0.8 }, { degree: 3, duration: 1, velocity: 0.8 }],
  "4": [{ degree: 4, duration: 0.5, velocity: 0.8 }, { degree: 5, duration: 0.5, velocity: 0.8 }, { degree: 3, duration: 0.5, velocity: 0.75 }, { degree: 4, duration: 0.5, velocity: 0.8 }, { degree: 5, duration: 1, velocity: 0.8 }],
  "5": [{ degree: 5, duration: 0.5, velocity: 0.8 }, { degree: 3, duration: 0.5, velocity: 0.8 }, { degree: 5, duration: 0.5, velocity: 0.75 }, { degree: 4, duration: 0.5, velocity: 0.8 }, { degree: 3, duration: 1, velocity: 0.8 }],
  "6": [{ degree: 6, duration: 0.5, velocity: 0.8 }, { degree: 5, duration: 0.5, velocity: 0.8 }, { degree: 4, duration: 0.5, velocity: 0.75 }, { degree: 3, duration: 0.5, velocity: 0.8 }, { degree: 1, duration: 1, velocity: 0.85 }],
  "7": [{ degree: 7, duration: 0.5, velocity: 0.8 }, { degree: 6, duration: 0.5, velocity: 0.8 }, { degree: 5, duration: 0.5, velocity: 0.75 }, { degree: 3, duration: 0.5, velocity: 0.8 }, { degree: 1, duration: 1, velocity: 0.85 }],
};

/** Parse melody_table.json at runtime; use result as params.MELODY_TABLE in trajectoryOrKeyToMotive / trajectoryToScore. */
export function parseMelodyTableFromJson(jsonString: string): MelodyTable {
  return JSON.parse(jsonString) as MelodyTable;
}

function keyToString(key: number[]): string {
  return key.join(",");
}

function notesFromTableValue(raw: Array<{ degree?: number; duration?: number; velocity?: number }>, rootMidi: number, mode: string): Note[] {
  const notes: Note[] = [];
  let t = 0;
  for (const item of raw) {
    const degree = item.degree ?? 1;
    const duration = item.duration ?? 0.5;
    const velocity = Math.max(0, Math.min(1, item.velocity ?? 0.8));
    const pitch = degreeToPitch(degree, rootMidi, mode);
    notes.push({ pitch, duration, velocity, start: t });
    t += duration;
  }
  return notes;
}

function fallbackMotive(rootMidi: number, mode: string): Note[] {
  return notesFromTableValue(
    [1, 3, 5, 3, 1].map((d) => ({ degree: d, duration: 0.5, velocity: 0.8 })),
    rootMidi,
    mode
  );
}

/** Longest-prefix lookup in melody table; useFallback when no match. */
export function lookupMelody(
  key: number[] | string,
  rootMidi: number,
  mode: string,
  table: MelodyTable | undefined = DEFAULT_MELODY_TABLE,
  useFallback: boolean = true
): Note[] {
  const keyArr = typeof key === "string" ? key.split(",").map((x) => parseInt(x.trim(), 10)) : key;
  const tbl = table ?? DEFAULT_MELODY_TABLE;
  for (let len = keyArr.length; len >= 1; len--) {
    const prefix = keyArr.slice(0, len);
    const k = keyToString(prefix);
    const raw = tbl[k];
    if (raw && raw.length > 0) return notesFromTableValue(raw, rootMidi, mode);
  }
  return useFallback ? fallbackMotive(rootMidi, mode) : [];
}

/** Input: trajectory (TrajectoryPoint[]) or key (number[]). Returns motive. */
export function trajectoryOrKeyToMotive(trajectoryOrKey: TrajectoryPoint[] | number[], params: Params = {}): Note[] {
  const p = { ...DEFAULT_PARAMS, ...params };
  const rootMidi = getP(p, "KEY_ROOT_MIDI", DEFAULT_PARAMS.KEY_ROOT_MIDI) as number;
  const mode = getP(p, "KEY_MODE", DEFAULT_PARAMS.KEY_MODE) as string;
  const keyLength = getP(p, "MELODY_KEY_LENGTH", DEFAULT_PARAMS.MELODY_KEY_LENGTH) as number;
  const useFallback = getP(p, "MELODY_FALLBACK", DEFAULT_PARAMS.MELODY_FALLBACK) as boolean;
  const table = (params as Params & { MELODY_TABLE?: MelodyTable }).MELODY_TABLE;
  const isTrajectory = Array.isArray(trajectoryOrKey) && trajectoryOrKey.length > 0 && typeof trajectoryOrKey[0] === "object" && "direction" in (trajectoryOrKey[0] as object);
  const key = isTrajectory ? trajectoryToKey(trajectoryOrKey as TrajectoryPoint[], rootMidi, mode, keyLength) : (trajectoryOrKey as number[]);
  return lookupMelody(key, rootMidi, mode, table, useFallback);
}
'''

    # ---------- composer.ts ----------
    composer_ts = r'''/**
 * Compose: motive + accompaniment + optional counterpoint + pad/bass/percussion/ornament → Score. Port from musician.composer.
 */

import type { Note, Score, Track } from "./types";
import type { Params } from "./defaults";
import { DEFAULT_PARAMS } from "./defaults";
import { getProgressionChords, intervalInScaleSteps, getScale, snapPitchToScale } from "./tonality";

const GM_KICK = 36;
const GM_SNARE = 38;

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

function counterpointSecondaryMelody(
  motive: Note[],
  rootMidi: number,
  mode: string,
  velocityRatio: number
): Note[] {
  const delayBeats = 4;
  const durationFactor = 1.4;
  const notes: Note[] = [];
  for (const n of motive) {
    const start = n.start + delayBeats;
    const dur = Math.min(n.duration * durationFactor, 2);
    const vel = Math.max(0, Math.min(1, n.velocity * velocityRatio * 0.9));
    const pitch = snapPitchToScale(n.pitch, rootMidi, mode);
    notes.push({ pitch, duration: dur, velocity: vel, start });
  }
  return notes;
}

function makePad(
  motive: Note[],
  chords: number[][],
  velocity: number,
  chordDuration: number,
  octaveOffset: number,
  rootMidi: number
): Note[] {
  if (!motive.length) return [];
  const endTime = Math.max(...motive.map((n) => n.start + n.duration));
  const notes: Note[] = [];
  let t = 0;
  let i = 0;
  while (t < endTime) {
    const triad = chords[i % chords.length]!;
    const pitch = Math.max(0, Math.min(127, rootMidi + 12 * octaveOffset + ((triad[1]! - rootMidi) % 12 + 12) % 12));
    notes.push({ pitch, duration: chordDuration, velocity, start: t });
    t += chordDuration;
    i++;
  }
  return notes;
}

function makeBass(
  motive: Note[],
  chords: number[][],
  velocity: number,
  style: string,
  octaveOffset: number,
  chordDuration: number
): Note[] {
  if (!motive.length) return [];
  const endTime = Math.max(...motive.map((n) => n.start + n.duration));
  const notes: Note[] = [];
  let t = 0;
  let i = 0;
  while (t < endTime) {
    const triad = chords[i % chords.length]!;
    const bassPitch = Math.max(0, Math.min(127, triad[0]! + 12 * octaveOffset));
    if (style === "root_fifth") {
      const fifthPitch = Math.max(0, Math.min(127, triad[2]! + 12 * octaveOffset));
      const half = chordDuration / 2;
      notes.push({ pitch: bassPitch, duration: half, velocity, start: t });
      notes.push({ pitch: fifthPitch, duration: half, velocity: velocity * 0.9, start: t + half });
    } else {
      notes.push({ pitch: bassPitch, duration: chordDuration, velocity, start: t });
    }
    t += chordDuration;
    i++;
  }
  return notes;
}

function makePercussion(motive: Note[], velocity: number, pattern: string, beatsPerBar: number): Note[] {
  if (!motive.length) return [];
  const endTime = Math.max(...motive.map((n) => n.start + n.duration));
  const notes: Note[] = [];
  let t = 0;
  const step = 0.5;
  while (t < endTime) {
    const barPos = t % beatsPerBar;
    if (pattern === "simple_44") {
      if (barPos < 0.05 || (barPos >= 1.95 && barPos < 2.05)) {
        notes.push({ pitch: GM_KICK, duration: 0.25, velocity, start: t });
      } else if ((barPos >= 0.95 && barPos < 1.05) || (barPos >= 2.95 && barPos < 3.05)) {
        notes.push({ pitch: GM_SNARE, duration: 0.25, velocity: velocity * 0.85, start: t });
      }
    }
    t += step;
  }
  return notes;
}

function makeOrnamentation(
  motive: Note[],
  rootMidi: number,
  mode: string,
  velocityRatio: number,
  density: number,
  maxDuration: number
): Note[] {
  const notes: Note[] = [];
  for (let i = 0; i < motive.length; i++) {
    const n = motive[i]!;
    if (Math.random() >= density) continue;
    const start = n.start + n.duration;
    const dur = Math.min(maxDuration, 0.25);
    const vel = Math.max(0, Math.min(1, n.velocity * velocityRatio));
    const pitch = (i % 2 === 0)
      ? intervalInScaleSteps(rootMidi, mode, n.pitch, 1)
      : intervalInScaleSteps(rootMidi, mode, n.pitch, -1);
    notes.push({ pitch, duration: dur, velocity: vel, start });
  }
  return notes;
}

export function compose(motive: Note[], params: Params = {}): Score {
  const p = { ...DEFAULT_PARAMS, ...params };
  const keyRoot = getP(p, "KEY_ROOT_MIDI", DEFAULT_PARAMS.KEY_ROOT_MIDI) as number;
  const keyMode = getP(p, "KEY_MODE", DEFAULT_PARAMS.KEY_MODE) as string;
  const bpm = getP(p, "COMPOSE_DEFAULT_BPM", DEFAULT_PARAMS.COMPOSE_DEFAULT_BPM) as number;
  const addAccompaniment = getP(p, "COMPOSE_ADD_ACCOMPANIMENT", DEFAULT_PARAMS.COMPOSE_ADD_ACCOMPANIMENT) as boolean;
  const accompVel = getP(p, "COMPOSE_ACCOMPANIMENT_VELOCITY", DEFAULT_PARAMS.COMPOSE_ACCOMPANIMENT_VELOCITY) as number;
  const accompStyle = getP(p, "COMPOSE_ACCOMPANIMENT_STYLE", DEFAULT_PARAMS.COMPOSE_ACCOMPANIMENT_STYLE) as string;
  const chordDuration = getP(p, "COMPOSE_CHORD_DURATION", DEFAULT_PARAMS.COMPOSE_CHORD_DURATION) as number;
  const arpNoteDur = getP(p, "COMPOSE_ARPEGGIO_NOTE_DURATION", DEFAULT_PARAMS.COMPOSE_ARPEGGIO_NOTE_DURATION) as number;
  const addCounterpoint = getP(p, "COMPOSE_ADD_COUNTERPOINT", DEFAULT_PARAMS.COMPOSE_ADD_COUNTERPOINT) as boolean;
  const counterpointStyle = getP(p, "COMPOSE_COUNTERPOINT_STYLE", DEFAULT_PARAMS.COMPOSE_COUNTERPOINT_STYLE) as string;
  const cptVelRatio = getP(p, "COMPOSE_COUNTERPOINT_VELOCITY_RATIO", DEFAULT_PARAMS.COMPOSE_COUNTERPOINT_VELOCITY_RATIO) as number;
  const addPad = getP(p, "COMPOSE_ADD_PAD", DEFAULT_PARAMS.COMPOSE_ADD_PAD) as boolean;
  const padVelocity = getP(p, "COMPOSE_PAD_VELOCITY", DEFAULT_PARAMS.COMPOSE_PAD_VELOCITY) as number;
  const padChordDuration = getP(p, "COMPOSE_PAD_CHORD_DURATION", DEFAULT_PARAMS.COMPOSE_PAD_CHORD_DURATION) as number;
  const padOctaveOffset = getP(p, "COMPOSE_PAD_OCTAVE_OFFSET", DEFAULT_PARAMS.COMPOSE_PAD_OCTAVE_OFFSET) as number;
  const addBass = getP(p, "COMPOSE_ADD_BASS", DEFAULT_PARAMS.COMPOSE_ADD_BASS) as boolean;
  const bassVelocity = getP(p, "COMPOSE_BASS_VELOCITY", DEFAULT_PARAMS.COMPOSE_BASS_VELOCITY) as number;
  const bassStyle = getP(p, "COMPOSE_BASS_STYLE", DEFAULT_PARAMS.COMPOSE_BASS_STYLE) as string;
  const bassOctaveOffset = getP(p, "COMPOSE_BASS_OCTAVE_OFFSET", DEFAULT_PARAMS.COMPOSE_BASS_OCTAVE_OFFSET) as number;
  const addPercussion = getP(p, "COMPOSE_ADD_PERCUSSION", DEFAULT_PARAMS.COMPOSE_ADD_PERCUSSION) as boolean;
  const percussionVelocity = getP(p, "COMPOSE_PERCUSSION_VELOCITY", DEFAULT_PARAMS.COMPOSE_PERCUSSION_VELOCITY) as number;
  const percussionPattern = getP(p, "COMPOSE_PERCUSSION_PATTERN", DEFAULT_PARAMS.COMPOSE_PERCUSSION_PATTERN) as string;
  const addOrnamentation = getP(p, "COMPOSE_ADD_ORNAMENTATION", DEFAULT_PARAMS.COMPOSE_ADD_ORNAMENTATION) as boolean;
  const ornamentVelocityRatio = getP(p, "COMPOSE_ORNAMENT_VELOCITY_RATIO", DEFAULT_PARAMS.COMPOSE_ORNAMENT_VELOCITY_RATIO) as number;
  const ornamentDensity = getP(p, "COMPOSE_ORNAMENT_DENSITY", DEFAULT_PARAMS.COMPOSE_ORNAMENT_DENSITY) as number;
  const ornamentMaxDuration = getP(p, "COMPOSE_ORNAMENT_MAX_DURATION", DEFAULT_PARAMS.COMPOSE_ORNAMENT_MAX_DURATION) as number;
  const num = getP(p, "TIME_SIGNATURE_NUMERATOR", DEFAULT_PARAMS.TIME_SIGNATURE_NUMERATOR) as number;
  const denom = getP(p, "TIME_SIGNATURE_DENOMINATOR", DEFAULT_PARAMS.TIME_SIGNATURE_DENOMINATOR) as number;
  const beatsPerBar = getP(p, "BEATS_PER_BAR", DEFAULT_PARAMS.BEATS_PER_BAR) as number;

  const chords = getProgressionChords(keyRoot, keyMode);
  const tracks: Track[] = [];
  const motiveNotes = motive.map((n) => ({ ...n }));
  tracks.push({ name: "motive", notes: motiveNotes });

  if (addAccompaniment && motive.length > 0) {
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

  if (addBass && motive.length > 0) {
    tracks.push({ name: "bass", notes: makeBass(motive, chords, bassVelocity, bassStyle, bassOctaveOffset, chordDuration) });
  }
  if (addPad && motive.length > 0) {
    tracks.push({ name: "pad", notes: makePad(motive, chords, padVelocity, padChordDuration, padOctaveOffset, keyRoot) });
  }

  if (addCounterpoint && motive.length > 0) {
    let cpt: Note[];
    if (counterpointStyle === "parallel_6th") {
      cpt = counterpointParallel(motive, keyRoot, keyMode, 5, cptVelRatio);
    } else if (counterpointStyle === "ostinato") {
      cpt = counterpointOstinato(motive, keyRoot, keyMode, cptVelRatio);
    } else if (counterpointStyle === "secondary_melody") {
      cpt = counterpointSecondaryMelody(motive, keyRoot, keyMode, cptVelRatio);
    } else {
      cpt = counterpointParallel(motive, keyRoot, keyMode, 2, cptVelRatio);
    }
    tracks.push({ name: "counterpoint", notes: cpt });
  }

  if (addOrnamentation && motive.length > 0) {
    tracks.push({ name: "ornamentation", notes: makeOrnamentation(motive, keyRoot, keyMode, ornamentVelocityRatio, ornamentDensity, ornamentMaxDuration) });
  }
  if (addPercussion && motive.length > 0) {
    tracks.push({ name: "percussion", notes: makePercussion(motive, percussionVelocity, percussionPattern, beatsPerBar) });
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
 * Input: motion trajectory OR scale-degree key (number[]) + optional params.
 * Output: Score (bpm, time_signature, tracks with notes: pitch, duration, velocity, start).
 *
 * Usage:
 *   import { trajectoryToScore } from "musician-ts-lib";
 *   const trajectory = [{ velocity: 0.5, direction: 180, intensity: 0.7 }, ...];
 *   const score = trajectoryToScore(trajectory, { MELODY_KEY_LENGTH: 5 });
 *   // Or pass key (scale degrees) directly:
 *   const score = trajectoryToScore([1, 3, 5, 3, 1], params);
 */

import type { TrajectoryPoint, Score } from "./types";
import type { Params } from "./defaults";
import { trajectoryOrKeyToMotive } from "./melodyTable";
import { compose } from "./composer";

export type { TrajectoryPoint, Note, Track, Score } from "./types";
export type { Params } from "./defaults";
export { DEFAULT_PARAMS } from "./defaults";

/**
 * Generate a Score from motion trajectory or from a key (scale degrees 1–7).
 * When trajectory is TrajectoryPoint[], key is derived and melody table is used.
 * When trajectory is number[], it is used as key to lookup melody directly.
 */
export function trajectoryToScore(
  trajectoryOrKey: TrajectoryPoint[] | number[],
  params: Params = {}
): Score {
  const motive = trajectoryOrKeyToMotive(trajectoryOrKey, params);
  return compose(motive, params);
}

export { trajectoryToKey, lookupMelody, trajectoryOrKeyToMotive, parseMelodyTableFromJson } from "./melodyTable";
export type { MelodyTable } from "./melodyTable";
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

'''

    files = [
        (os.path.join(src, "types.ts"), types_ts),
        (os.path.join(src, "defaults.ts"), defaults_ts),
        (os.path.join(src, "tonality.ts"), tonality_ts),
        (os.path.join(src, "rng.ts"), rng_ts),
        (os.path.join(src, "melodyTable.ts"), melody_table_ts),
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
