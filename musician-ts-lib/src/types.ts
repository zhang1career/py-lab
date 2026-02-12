/**
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
