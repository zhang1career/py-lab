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

export type MelodyEntry = {
  notes: Array<{ d?: number; dur?: number; vel?: number; degree?: number; duration?: number; velocity?: number }>;
  /** Root as note name (a～g, a#～g#) or MIDI number; converted to MIDI when string. */
  key_root?: string | number;
  KEY_ROOT_MIDI?: number;
  KEY_MODE?: string;
  key_mode?: string;
  /** Optional per-melody time signature override (replaces TIME_SIGNATURE_* / BEATS_PER_BAR when both present). */
  time_sign_numerator?: number;
  time_sign_denominator?: number;
  /** Optional per-melody BPM override (overrides COMPOSE_DEFAULT_BPM at runtime). */
  bpm?: number;
};

export type MelodyOverrides = { time_sign_numerator?: number; time_sign_denominator?: number; bpm?: number };
/** Tree: key 1–7 → leaf = MelodyEntry[] (candidates), inner = MelodyTable (next level). */
export interface MelodyTable {
  [key: string]: MelodyEntry[] | MelodyTable;
}

const KEY_ROOT_SEMITONE: Record<string, number> = {
  c: 0, "c#": 1, d: 2, "d#": 3, e: 4, f: 5, "f#": 6,
  g: 7, "g#": 8, a: 9, "a#": 10, b: 11,
};

/** Note name (a～g, a#～g#) → MIDI. Default octave 4 → C4=60. */
function keyRootToMidi(noteName: string, octave: number = 4): number {
  const s = noteName.trim().toLowerCase().replace(/♯/g, "#");
  const semitone = KEY_ROOT_SEMITONE[s];
  if (semitone === undefined) throw new Error(`invalid key_root: ${JSON.stringify(noteName)}, expected a～g or a#～g#`);
  return Math.max(0, Math.min(127, (octave + 1) * 12 + semitone));
}

const DEFAULT_MELODY_TABLE: MelodyTable = {
  "1": [{ notes: [{ d: 1, dur: 0.5, vel: 0.85 }, { d: 3, dur: 0.5, vel: 0.8 }, { d: 5, dur: 0.5, vel: 0.8 }, { d: 3, dur: 0.5, vel: 0.75 }, { d: 1, dur: 1, vel: 0.8 }] }],
  "2": [{ notes: [{ d: 2, dur: 0.5, vel: 0.8 }, { d: 4, dur: 0.5, vel: 0.8 }, { d: 5, dur: 0.5, vel: 0.75 }, { d: 3, dur: 0.5, vel: 0.8 }, { d: 1, dur: 1, vel: 0.85 }] }],
  "3": [{ notes: [{ d: 3, dur: 0.5, vel: 0.8 }, { d: 5, dur: 0.5, vel: 0.8 }, { d: 3, dur: 0.5, vel: 0.75 }, { d: 1, dur: 0.5, vel: 0.8 }, { d: 3, dur: 1, vel: 0.8 }], time_sign_numerator: 3, time_sign_denominator: 4 }],
  "4": [{ notes: [{ d: 4, dur: 0.5, vel: 0.8 }, { d: 5, dur: 0.5, vel: 0.8 }, { d: 3, dur: 0.5, vel: 0.75 }, { d: 4, dur: 0.5, vel: 0.8 }, { d: 5, dur: 1, vel: 0.8 }] }],
  "5": [{ notes: [{ d: 5, dur: 0.5, vel: 0.8 }, { d: 3, dur: 0.5, vel: 0.8 }, { d: 5, dur: 0.5, vel: 0.75 }, { d: 4, dur: 0.5, vel: 0.8 }, { d: 3, dur: 1, vel: 0.8 }] }],
  "6": [{ notes: [{ d: 6, dur: 0.5, vel: 0.8 }, { d: 5, dur: 0.5, vel: 0.8 }, { d: 4, dur: 0.5, vel: 0.75 }, { d: 3, dur: 0.5, vel: 0.8 }, { d: 1, dur: 1, vel: 0.85 }] }],
  "7": [{ KEY_MODE: "minor", notes: [{ d: 7, dur: 0.5, vel: 0.8 }, { d: 6, dur: 0.5, vel: 0.8 }, { d: 5, dur: 0.5, vel: 0.75 }, { d: 3, dur: 0.5, vel: 0.8 }, { d: 1, dur: 1, vel: 0.85 }] }],
};

/** Parse melody_table.json at runtime; use result as params.MELODY_TABLE in trajectoryOrKeyToMotive / trajectoryToScore. */
export function parseMelodyTableFromJson(jsonString: string): MelodyTable {
  return JSON.parse(jsonString) as MelodyTable;
}

function normalizeTableValue(raw: MelodyEntry | undefined, defaultRootMidi: number, defaultMode: string): [MelodyEntry["notes"], number, string, MelodyOverrides] {
  const emptyOverrides: MelodyOverrides = {};
  if (!raw || !Array.isArray(raw.notes) || raw.notes.length === 0) return [[], defaultRootMidi, defaultMode, emptyOverrides];
  let rootMidi: number;
  const kr = raw.key_root;
  if (kr !== undefined && kr !== null) {
    rootMidi = typeof kr === "string" ? keyRootToMidi(kr) : Math.max(0, Math.min(127, kr));
  } else if (raw.KEY_ROOT_MIDI !== undefined && raw.KEY_ROOT_MIDI !== null) {
    rootMidi = raw.KEY_ROOT_MIDI;
  } else {
    rootMidi = defaultRootMidi;
  }
  const mode = raw.key_mode ?? raw.KEY_MODE ?? defaultMode;
  const overrides: MelodyOverrides = {};
  const num = raw.time_sign_numerator;
  const denom = raw.time_sign_denominator;
  if (num != null && denom != null && num > 0 && denom > 0) {
    overrides.time_sign_numerator = num;
    overrides.time_sign_denominator = denom;
  }
  const bpmVal = raw.bpm;
  if (bpmVal != null && typeof bpmVal === "number" && bpmVal > 0) {
    overrides.bpm = bpmVal;
  }
  return [raw.notes, rootMidi, mode, overrides];
}

function notesFromTableValue(raw: MelodyEntry["notes"], rootMidi: number, mode: string): Note[] {
  const notes: Note[] = [];
  let t = 0;
  for (const item of raw) {
    const degree = item.d ?? item.degree ?? 1;
    const duration = item.dur ?? item.duration ?? 0.5;
    const velocity = Math.max(0, Math.min(1, item.vel ?? item.velocity ?? 0.8));
    const pitch = degreeToPitch(degree, rootMidi, mode);
    notes.push({ pitch, duration, velocity, start: t });
    t += duration;
  }
  return notes;
}

function fallbackMotive(rootMidi: number, mode: string): Note[] {
  return notesFromTableValue(
    [1, 3, 5, 3, 1].map((d) => ({ d, dur: 0.5, vel: 0.8 })),
    rootMidi,
    mode
  );
}

/** Recursively collect all MelodyEntry from a tree node (leaf array or inner MelodyTable). Used when key stops at inner node. */
function collectAllEntries(node: MelodyEntry[] | MelodyTable): MelodyEntry[] {
  const out: MelodyEntry[] = [];
  if (Array.isArray(node)) {
    for (const item of node) {
      if (item && Array.isArray(item.notes)) out.push(item);
    }
    return out;
  }
  for (const child of Object.values(node)) {
    out.push(...collectAllEntries(child as MelodyEntry[] | MelodyTable));
  }
  return out;
}

/** Tree longest-prefix lookup: follow key sequence into tree; leaf = array of MelodyEntry, pick one at random. If we stop at an inner node, collect all descendant melodies and pick one at random. */
function lookupTree(tbl: MelodyTable, keyArr: number[]): MelodyEntry | undefined {
  let node: MelodyEntry[] | MelodyTable = tbl;
  for (const d of keyArr) {
    if (Array.isArray(node)) break;
    const k = String(d);
    if (!(k in node)) break;
    node = (node as MelodyTable)[k];
  }
  if (Array.isArray(node) && node.length > 0) {
    const entry = node[Math.floor(Math.random() * node.length)] as MelodyEntry;
    if (entry && Array.isArray(entry.notes)) return entry;
  }
  if (!Array.isArray(node) && typeof node === "object" && node !== null) {
    const candidates = collectAllEntries(node as MelodyTable);
    if (candidates.length > 0) {
      return candidates[Math.floor(Math.random() * candidates.length)];
    }
  }
  return undefined;
}

export function lookupMelody(
  key: number[] | string,
  rootMidi: number,
  mode: string,
  table: MelodyTable | undefined = DEFAULT_MELODY_TABLE,
  useFallback: boolean = true
): [Note[], MelodyOverrides] {
  const keyArr = typeof key === "string" ? key.split(",").map((x) => parseInt(x.trim(), 10)) : key;
  const tbl = table ?? DEFAULT_MELODY_TABLE;
  const raw = lookupTree(tbl, keyArr);
  if (raw) {
    const [notesList, resolvedRootMidi, resolvedMode, overrides] = normalizeTableValue(raw, rootMidi, mode);
    if (notesList.length > 0) return [notesFromTableValue(notesList, resolvedRootMidi, resolvedMode), overrides];
  }
  return useFallback ? [fallbackMotive(rootMidi, mode), {}] : [[], {}];
}

/** Input: trajectory (TrajectoryPoint[]) or key (number[]). Returns [motive, overrides]. */
export function trajectoryOrKeyToMotive(trajectoryOrKey: TrajectoryPoint[] | number[], params: Params = {}): [Note[], MelodyOverrides] {
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
