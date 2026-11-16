// The arithmetic of ImageViewer: scale, pan and the two-finger gesture, with no DOM in it.
export type Point = { x: number; y: number };
export type Size = { w: number; h: number };

export const MIN_SCALE = 1;
export const MAX_SCALE = 5;
/** One press of a zoom button or key. */
export const STEP = 1.5;

export function clampScale(scale: number): number {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale));
}

export function stepScale(scale: number, direction: 1 | -1): number {
  return clampScale(direction === 1 ? scale * STEP : scale / STEP);
}

/**
 * The pan that keeps the point under `anchor` (measured from the stage's centre) where it is while the
 * scale goes from `from` to `to`. The picture is drawn as translate, rotate, scale, so the rotation drops out.
 */
export function anchoredPan(
  pan: Point,
  anchor: Point,
  from: number,
  to: number,
): Point {
  const k = to / from;
  return {
    x: anchor.x - k * (anchor.x - pan.x),
    y: anchor.y - k * (anchor.y - pan.y),
  };
}

/** The pan, held so that the picture never moves further than it overflows the stage. */
export function clampPan(pan: Point, content: Size, stage: Size): Point {
  const reach = (content: number, stage: number) =>
    Math.max(0, (content - stage) / 2);
  const x = reach(content.w, stage.w);
  const y = reach(content.h, stage.h);
  return {
    x: Math.min(x, Math.max(-x, pan.x)),
    y: Math.min(y, Math.max(-y, pan.y)),
  };
}

export function distance(a: Point, b: Point): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

export function midpoint(a: Point, b: Point): Point {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}
