/**
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
