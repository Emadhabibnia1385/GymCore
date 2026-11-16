import { SERIES_TONES, type SeriesTone } from './chartTones';
import { areaPath, dotPath, linePath, runsOf, type XY } from './chartMath';

const W = 100;
const H = 32;
const PAD = 3;

type SparklineProps = {
  /** The series, oldest first. A null is a gap (no observation), never a zero. */
  data: readonly (number | null)[];
  /** What a screen reader hears for the picture: the range and the latest figure, in words. */
  summary: string;
  /** `"neutral"` is for a series that is context, not the figure itself. */
  tone?: SeriesTone;
  /** `"area"` fills under the line, `"line"` is the line alone. */
  variant?: 'area' | 'line';
  className?: string;
  'data-testid'?: string;
};

// A tiny line of a series: no axes, no text, the shape only (the figure beside it carries the number).
// Time runs from the left, as in `ColumnChart`. Server-renderable.
export function Sparkline({
  data,
  summary,
  tone = 'accent',
  variant = 'area',
  className,
  'data-testid': testId,
}: SparklineProps) {
  const runs = runsOf(data);
  const values = runs.flat().map((dot) => dot.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const x = (index: number) =>
    data.length > 1 ? (index / (data.length - 1)) * W : W / 2;
  const y = (value: number) =>
    max === min
      ? H / 2
      : PAD + (1 - (value - min) / (max - min)) * (H - PAD * 2);
  const colours = SERIES_TONES[tone];
  const latest = runs.at(-1)?.at(-1);
  const drawn = runs.map((run) => ({
    key: run[0]!.index,
    points: run.map((dot): XY => ({ x: x(dot.index), y: y(dot.value) })),
  }));
  const dots = new Set<number>(
    runs.filter((run) => run.length === 1).map((run) => run[0]!.index),
  );
  if (latest) dots.add(latest.index);
  return (
    <svg
      role="img"
      aria-label={summary}
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="none"
      className={['block h-10 w-full overflow-visible', className]
        .filter(Boolean)
        .join(' ')}
      data-testid={testId}
    >
      {values.length === 0 ? (
        <line
          data-part="baseline"
          x1={0}
          x2={W}
          y1={H - 0.5}
          y2={H - 0.5}
          className="stroke-field-border"
          strokeWidth={1}
          vectorEffect="non-scaling-stroke"
        />
      ) : null}
      {variant === 'area'
        ? drawn
            .filter((run) => run.points.length > 1)
            .map((run) => (
              <path
                key={run.key}
                data-part="area"
                d={areaPath(run.points, H)}
                className={colours.fill}
                stroke="none"
              />
            ))
        : null}
      {drawn
        .filter((run) => run.points.length > 1)
        .map((run) => (
          <path
            key={run.key}
            data-part="line"
            d={linePath(run.points)}
            className={colours.stroke}
            fill="none"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />
        ))}
      {[...dots].map((index) => (
        <path
          key={index}
          data-part="dot"
          d={dotPath({ x: x(index), y: y(data[index]!) })}
          className={colours.stroke}
          fill="none"
          strokeWidth={6}
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      ))}
    </svg>
  );
}
