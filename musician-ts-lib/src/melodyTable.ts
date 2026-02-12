/**
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
