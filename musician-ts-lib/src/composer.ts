/**
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
