'use client';

import {
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
  useId,
  useState,
} from 'react';
import { tv } from 'tailwind-variants';
import { t } from '../strings';
import { SERIES_TONES, type SeriesTone } from './chartTones';
import { areaPath, linePath, runsOf, type XY } from './chartMath';
import { type ChartTable, ChartTableDisclosure } from './chartTable';

/*
 * A time series in plain SVG and HTML, one or two series, no chart library. The picture only shows the
 * shape: every figure is text (a tooltip on hover and focus, a sentence for a screen reader, a data table).
 * The plot is left to right whatever the page direction, as in `ColumnChart`: time runs from the left.
 * Lines are SVG stretched to the box with strokes that keep their width; what must stay round or
 * readable (the dots, the labels, the tooltip) is HTML laid over it at the same percentages.
 */

const W = 1000;
const H = 200;
// The room above the highest gridline, so a line that reaches it is not cut off.
const TOP = 12;

const area = tv({
  slots: {
    figure: 'flex flex-col gap-2',
    caption: 'text-sm font-semibold text-foreground',
    legend: 'flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted',
    plot: 'relative w-full rounded-md bg-surface-secondary outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--focus) touch-pan-y',
    gutter: 'relative shrink-0 text-xs text-muted tabular-nums',
    ticks: 'relative h-4 flex-1 text-xs text-muted',
    dot: 'pointer-events-none absolute size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface',
    tooltip:
      'pointer-events-none absolute bottom-full z-10 mb-2 w-max max-w-64 rounded-md border border-border bg-overlay px-2.5 py-1.5 text-xs text-foreground shadow-overlay',
    empty:
      'rounded-md border border-dashed border-field-border p-4 text-center text-sm text-muted',
  },
  variants: {
    size: {
      md: { plot: 'h-40', gutter: 'h-40' },
      lg: { plot: 'h-56', gutter: 'h-56' },
    },
  },
  defaultVariants: { size: 'md' },
});

/** One step of time: the axis label and the full name used by the tooltip and the table. */
export type AreaTick = {
  key: string;
  /** The short label on the axis (a day of the month); an empty one leaves this step unlabelled. */
  label: string;
  /** The step in full («۱۲ مهر ۱۴۰۵»): the tooltip's heading and the table's row header. */
  title: string;
};

export type AreaPoint = {
  /** The height of the point only; a `null` is a gap (no observation), never a zero. */
  value: number | null;
  /** The exact figure as text («۱٬۲۰۰٬۰۰۰ تومان»): the tooltip, the table and the announcement. */
  text: string;
};

export type AreaSeries = {
  key: string;
  /** Names the series in the legend, the tooltip and the table. */
  label: string;
  /** One point per tick; a missing one is a gap. */
  points: readonly AreaPoint[];
  /** The first series defaults to `"accent"`, the second (the one compared with) to `"neutral"`. */
  tone?: SeriesTone;
};

type AreaChartProps = {
  /** The chart's caption. */
  title: string;
  /** What a screen reader hears for the picture: the range, the peak and the latest figure. */
  summary: string;
  /** Draws `summary` as a line under the title too. */
  showSummary?: boolean;
  /** The steps of time, oldest first. */
  ticks: readonly AreaTick[];
  /** One series, or two drawn over each other (the second dashed). */
  series: readonly [AreaSeries] | readonly [AreaSeries, AreaSeries];
  /** Gridlines and their labels, in the app's units (`{ value: 20, label: '۲۰ هزار' }`). Zero is always drawn. */
  yTicks?: readonly { value: number; label: string }[];
  /** Shown instead of the picture when no value is above zero. */
  empty: string;
  /** The words of the table that holds every figure as text; its rows come from `ticks` and `series`. */
  table: Pick<ChartTable, 'showLabel' | 'label'> & { stepHeader: string };
  /** A line under the chart: how the heights are scaled. */
  note?: ReactNode;
  size?: 'md' | 'lg';
  /** Also on `${data-testid}-table`. */
  'data-testid'?: string;
};

const clamp = (value: number, max: number) => Math.min(Math.max(value, 0), max);

// A one- or two-series area chart. Hover, touch and the arrow keys choose a step; the step's tooltip has
// the exact figures.
export function AreaChart({
  title,
  summary,
  showSummary = false,
  ticks,
  series,
  yTicks = [],
  empty,
  table,
  note,
  size,
  'data-testid': testId,
}: AreaChartProps) {
  const captionId = useId();
  const hintId = useId();
  const [active, setActive] = useState<number | null>(null);
  const [byKeys, setByKeys] = useState(false);
  const slots = area({ size });
  const last = ticks.length - 1;
  const values = series.flatMap((one) =>
    one.points.map((point) => point.value),
  );
  const top = Math.max(
    0,
    ...yTicks.map((tick) => tick.value),
    ...values.map((v) => v ?? 0),
  );
  const drawn = ticks.length > 0 && values.some((value) => (value ?? 0) > 0);
  const x = (index: number) => (last > 0 ? (index / last) * W : W / 2);
  const y = (value: number) => H - (value / top) * (H - TOP);
  const percent = (index: number) => (last > 0 ? (index / last) * 100 : 50);
  const drawnSeries = series.map((one, order) => ({
    ...one,
    tone: SERIES_TONES[one.tone ?? (order === 0 ? 'accent' : 'neutral')],
    runs: runsOf(ticks.map((_, index) => one.points[index]?.value ?? null)),
    dashed: order === 1,
  }));
  const figures = (index: number) =>
    series.map((one) => ({
      label: one.label,
      text:
        one.points[index]?.value == null
          ? t.areaChart.noData
          : one.points[index].text,
    }));
  const heard =
    active === null
      ? ''
      : `${ticks[active]!.title}: ${figures(active)
          .map((figure) => `${figure.label} ${figure.text}`)
          .join('، ')}`;

  const choose = (index: number, keys: boolean) => {
    setActive(clamp(index, last));
    setByKeys(keys);
  };
  const point = (event: PointerEvent<HTMLElement>) => {
    const box = event.currentTarget.getBoundingClientRect();
    if (box.width > 0)
      choose(
        Math.round(((event.clientX - box.left) / box.width) * last),
        false,
      );
  };
  const key = (event: KeyboardEvent<HTMLElement>) => {
    const from = active ?? last + 1;
    const next: Record<string, number | undefined> = {
      ArrowLeft: from - 1,
      ArrowRight: from + 1,
      Home: 0,
      End: last,
    };
    if (event.key === 'Escape') {
      setActive(null);
      return;
    }
    const to = next[event.key];
    if (to === undefined) return;
    event.preventDefault();
    choose(to, true);
  };

  const rows = ticks.map((tick, index) => ({
    key: tick.key,
    cells: [tick.title, ...figures(index).map((figure) => figure.text)],
  }));

  return (
    <figure
      className={slots.figure()}
      aria-labelledby={captionId}
      data-testid={testId}
    >
      <figcaption id={captionId} className={slots.caption()}>
        {title}
      </figcaption>
      {showSummary ? <p className="text-sm text-muted">{summary}</p> : null}
      {series.length > 1 ? (
        <ul className={slots.legend()}>
          {drawnSeries.map((one) => (
            <li key={one.key} className="flex items-center gap-1.5">
              <svg
                aria-hidden
                viewBox="0 0 16 4"
                className={`h-1 w-4 ${one.tone.swatch}`}
              >
                <line
                  x1={0}
                  x2={16}
                  y1={2}
                  y2={2}
                  stroke="currentColor"
                  strokeWidth={2}
                  strokeDasharray={one.dashed ? '4 3' : undefined}
                />
              </svg>
              {one.label}
            </li>
          ))}
        </ul>
      ) : null}
      {drawn ? (
        <div
          dir="ltr"
          className={`grid gap-x-2 gap-y-1 ${yTicks.length ? 'grid-cols-[auto_1fr]' : 'grid-cols-1'}`}
        >
          {yTicks.length ? (
            <div aria-hidden className={slots.gutter()}>
              {/* Sizes the gutter to the widest label; the visible ones sit on their lines. */}
              <div className="invisible h-0 overflow-hidden">
                {yTicks.map((tick) => (
                  <div key={tick.value} className="whitespace-nowrap">
                    {tick.label}
                  </div>
                ))}
              </div>
              {yTicks.map((tick) => (
                <span
                  key={tick.value}
                  className="absolute end-0 -translate-y-1/2 whitespace-nowrap"
                  style={{ top: `${(y(tick.value) / H) * 100}%` }}
                >
                  {tick.label}
                </span>
              ))}
            </div>
          ) : null}
          <div
            role="group"
            aria-label={summary}
            aria-describedby={hintId}
            tabIndex={0}
            className={slots.plot()}
            onKeyDown={key}
            onFocus={() => {
              setActive((current) => current ?? last);
              setByKeys(true);
            }}
            onBlur={() => setActive(null)}
            onPointerMove={point}
            onPointerDown={point}
            onPointerLeave={(event) => {
              if (event.pointerType === 'mouse') setActive(null);
            }}
          >
            <svg
              aria-hidden
              viewBox={`0 0 ${W} ${H}`}
              preserveAspectRatio="none"
              className="absolute inset-0 size-full overflow-visible"
            >
              {yTicks
                .filter((tick) => tick.value > 0)
                .map((tick) => (
                  <line
                    key={tick.value}
                    data-part="grid"
                    x1={0}
                    x2={W}
                    y1={y(tick.value)}
                    y2={y(tick.value)}
                    className="stroke-border"
                    strokeWidth={1}
                    vectorEffect="non-scaling-stroke"
                  />
                ))}
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
              {drawnSeries.map((one) =>
                one.runs
                  .filter((run) => run.length > 1)
                  .map((run) => {
                    const points = run.map((dot): XY => ({
                      x: x(dot.index),
                      y: y(dot.value),
                    }));
                    return (
                      <g key={`${one.key}-${run[0]!.index}`}>
                        <path
                          data-part="area"
                          d={areaPath(points, H)}
                          className={one.tone.fill}
                          stroke="none"
                        />
                        <path
                          data-part="line"
                          d={linePath(points)}
                          className={one.tone.stroke}
                          fill="none"
                          strokeWidth={2}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeDasharray={one.dashed ? '6 4' : undefined}
                          vectorEffect="non-scaling-stroke"
                        />
                      </g>
                    );
                  }),
              )}
              {active !== null ? (
                <line
                  data-part="cursor"
                  x1={x(active)}
                  x2={x(active)}
                  y1={0}
                  y2={H}
                  className="stroke-muted"
                  strokeWidth={1}
                  strokeDasharray="3 3"
                  vectorEffect="non-scaling-stroke"
                />
              ) : null}
            </svg>
            {drawnSeries.map((one) => {
              const latest = one.runs.at(-1)?.at(-1);
              return latest ? (
                <span
                  key={one.key}
                  aria-hidden
                  data-part="latest"
                  className={`${slots.dot()} ${one.tone.bg}`}
                  style={{
                    left: `${percent(latest.index)}%`,
                    top: `${(y(latest.value) / H) * 100}%`,
                  }}
                />
              ) : null;
            })}
            {active !== null
              ? drawnSeries.map((one) => {
                  const value = one.points[active]?.value;
                  return value == null ? null : (
                    <span
                      key={one.key}
                      aria-hidden
                      data-part="active"
                      className={`${slots.dot()} ${one.tone.bg}`}
                      style={{
                        left: `${percent(active)}%`,
                        top: `${(y(value) / H) * 100}%`,
                      }}
                    />
                  );
                })
              : null}
            {active !== null ? (
              <div
                aria-hidden
                dir="auto"
                data-slot="area-tooltip"
                className={slots.tooltip()}
                style={{
                  left: `${percent(active)}%`,
                  transform: `translateX(-${percent(active)}%)`,
                }}
              >
                <p className="font-semibold">{ticks[active]!.title}</p>
                <ul className="mt-1 flex flex-col gap-0.5">
                  {drawnSeries.map((one, order) => (
                    <li
                      key={one.key}
                      className="flex items-center justify-between gap-3"
                    >
                      <span className="flex items-center gap-1.5 text-muted">
                        <span
                          className={`size-2 rounded-full ${one.tone.bg}`}
                        />
                        {one.label}
                      </span>
                      <span className="tabular-nums">
                        {figures(active)[order]!.text}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
          {yTicks.length ? <div /> : null}
          <div aria-hidden data-part="x-labels" className={slots.ticks()}>
            {ticks.map((tick, index) =>
              tick.label ? (
                <span
                  key={tick.key}
                  className={`absolute whitespace-nowrap ${index === 0 ? '' : index === last ? '-translate-x-full' : '-translate-x-1/2'}`}
                  style={{ left: `${percent(index)}%` }}
                >
                  {tick.label}
                </span>
              ) : null,
            )}
          </div>
          <p id={hintId} className="sr-only">
            {t.areaChart.hint}
          </p>
          <p className="sr-only" aria-live="polite">
            {byKeys ? heard : ''}
          </p>
        </div>
      ) : (
        <p className={slots.empty()}>{empty}</p>
      )}
      {note ? <p className="text-xs text-muted">{note}</p> : null}
      {ticks.length > 0 ? (
        <ChartTableDisclosure
          table={{
            showLabel: table.showLabel,
            label: table.label,
            columns: [table.stepHeader, ...series.map((one) => one.label)],
            rows,
          }}
          data-testid={testId ? `${testId}-table` : undefined}
        />
      ) : null}
    </figure>
  );
}
