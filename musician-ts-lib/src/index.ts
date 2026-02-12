/**
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
