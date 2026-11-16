// The little geometry the SVG charts share. A point is a value at an index; a null value is a gap.
export type Dot = { index: number; value: number };
export type XY = { x: number; y: number };

/** The runs of consecutive values: a null value ends one run and starts the next. */
export function runsOf(values: readonly (number | null)[]): Dot[][] {
  const runs: Dot[][] = [];
  let run: Dot[] = [];
  values.forEach((value, index) => {
    if (value === null || !Number.isFinite(value)) {
      if (run.length) runs.push(run);
      run = [];
    } else run.push({ index, value });
  });
  if (run.length) runs.push(run);
  return runs;
}

const round = (value: number) => Number(value.toFixed(2));

export function linePath(points: readonly XY[]): string {
  return points
    .map((point, at) => `${at ? 'L' : 'M'}${round(point.x)} ${round(point.y)}`)
    .join(' ');
}

/** The line closed down to the baseline, for the area under it. */
export function areaPath(points: readonly XY[], baseline: number): string {
  const first = points[0]!;
  const last = points[points.length - 1]!;
  return `${linePath(points)} L${round(last.x)} ${round(baseline)} L${round(first.x)} ${round(baseline)} Z`;
}

/** A round dot that stays round in a stretched box: a zero-length stroke with round caps. */
export function dotPath({ x, y }: XY): string {
  return `M${round(x)} ${round(y)}h0`;
}
