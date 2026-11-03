/** Timing for editorial marks on a painting explainer.
 * Camera motion stays on every frame of `video.fps`. Strokes step at ~12fps.
 * This file does not import Remotion or @remotion/rough-notation.
 */

export const ANNOTATION_KINDS = ['underline', 'circle', 'highlight', 'bracket'] as const;
export type AnnotationKind = (typeof ANNOTATION_KINDS)[number];

export const DESK_MATERIALS = ['map', 'letter', 'photo', 'document'] as const;
export type DeskMaterial = (typeof DESK_MATERIALS)[number];

export const DESK_LAYERS = ['desk', 'cutout', 'occlusion'] as const;

/** Map a plan `kind` to the official package. Install it only in the Remotion app. */
export const ROUGH_NOTATION_COMPONENT: Record<AnnotationKind, string> = {
  underline: 'Underline',
  circle: 'Circle',
  highlight: 'Highlight',
  bracket: 'Bracket',
};

export function isAnnotationKind(value: string): value is AnnotationKind {
  return (ANNOTATION_KINDS as readonly string[]).includes(value);
}

export function isDeskMaterial(value: string): value is DeskMaterial {
  return (DESK_MATERIALS as readonly string[]).includes(value);
}

function assertClock(frame: number, fps: number) {
  if (!Number.isFinite(frame) || !Number.isFinite(fps) || fps <= 0) {
    throw new Error('frame must be finite and fps must be positive');
  }
}

/** Hold element motion on a coarser clock. Equal fps is a no-op; a finer clock is rejected. */
export function steppedElementFrame(frame: number, fps: number, elementFps = 12): number {
  assertClock(frame, fps);
  if (!Number.isFinite(elementFps) || elementFps <= 0 || elementFps > fps) {
    throw new Error('element fps must be positive and no finer than the camera');
  }
  if (frame <= 0) return 0;
  const step = fps / elementFps;
  return Math.floor(frame / step) * step;
}

/** Underdamped approach from 0 toward 1. The value may pass 1, then settle. */
export function springTowardOne(frame: number, fps: number): number {
  assertClock(frame, fps);
  if (frame <= 0) return 0;
  const t = frame / fps;
  const mass = 0.65;
  const stiffness = 170;
  const damping = 14;
  const omega0 = Math.sqrt(stiffness / mass);
  const zeta = damping / (2 * Math.sqrt(stiffness * mass));
  const omegaD = omega0 * Math.sqrt(1 - zeta * zeta);
  const envelope = Math.exp(-zeta * omega0 * t);
  const displacement = envelope * (
    Math.cos(omegaD * t) + (zeta * omega0 / omegaD) * Math.sin(omegaD * t)
  );
  return 1 - displacement;
}

export type MarkerDraw = {opacity: number; draw: number; scale: number};

/** Hard appearance at frame 0 (opacity is 0 or 1). The stroke draws on the element clock. */
export function markerDraw(frame: number, fps: number, elementFps = 12): MarkerDraw {
  assertClock(frame, fps);
  if (frame < 0) return {opacity: 0, draw: 0, scale: 1};
  const stepped = steppedElementFrame(frame, fps, elementFps);
  const t = stepped / fps;
  const draw = Math.max(0, Math.min(1, 1 - Math.exp(-t / 0.16)));
  const scale = 0.96 + 0.04 * springTowardOne(stepped, fps);
  return {opacity: 1, draw, scale};
}

export type VoWord = {id: string; start: number; end: number};

/** The spoken word is the clock. The mark starts when that word starts. */
export function citationWindow(
  words: readonly VoWord[], wordId: string, holdSeconds: number,
): {start: number; end: number} {
  if (!Number.isFinite(holdSeconds) || holdSeconds <= 0) {
    throw new Error('hold must be a positive number of seconds');
  }
  const word = words.find(item => item.id === wordId);
  if (!word) throw new Error('unknown word');
  if (!Number.isFinite(word.start) || !Number.isFinite(word.end) || word.end <= word.start) {
    throw new Error('word needs a finite interval');
  }
  return {start: word.start, end: word.start + holdSeconds};
}

export type Box = {x: number; y: number; width: number; height: number};

/** Slots for a non-painting archival desk. The painting never goes in these boxes. */
export function evidenceDeskLayout(width: number, height: number): {
  desk: Box; cutout: Box; marker: Box; occlusion: Box;
} {
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    throw new Error('canvas dimensions must be positive');
  }
  const desk = {x: 0, y: 0, width, height};
  const cutout = {x: width * 0.08, y: height * 0.12, width: width * 0.84, height: height * 0.58};
  const marker = {
    x: cutout.x - width * 0.015,
    y: cutout.y + height * 0.012,
    width: cutout.width,
    height: cutout.height,
  };
  const occlusion = {x: width * 0.58, y: height * 0.62, width: width * 0.36, height: height * 0.24};
  return {desk, cutout, marker, occlusion};
}
