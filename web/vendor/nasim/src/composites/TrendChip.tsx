import { chipVariants } from '@heroui/styles';
import type { ReactNode } from 'react';
import { tv } from 'tailwind-variants';
import { ArrowDownIcon, ArrowUpIcon, FlatIcon } from '../icons';
import { formatChange, t } from '../strings';

type Trend = 'up' | 'down' | 'flat';

// The same soft pairs as `StatusChip`: coloured text on its own tint, 4.5:1 in both themes.
const trendChip = tv({
  base: 'gap-1 font-semibold tabular-nums',
  variants: {
    tone: {
      success: 'bg-success-soft text-success-soft-foreground',
      danger: 'bg-danger-soft text-danger-soft-foreground',
      neutral: 'bg-default text-default-foreground',
    },
  },
});

const ARROWS = {
  up: ArrowUpIcon,
  down: ArrowDownIcon,
  flat: FlatIcon,
} as const;

type TrendChipProps = {
  /** The change against the previous period as a fraction: 0.12 is +12%, -0.034 is -3.4%. */
  change: number;
  /** Down is good (cost, refunds, errors): the colours swap, the arrow and the sign do not. */
  isInverse?: boolean;
  /** What it is compared with, in the app's words («نسبت به ماه قبل»), after the chip. */
  suffix?: ReactNode;
  size?: 'sm' | 'md';
  className?: string;
  'data-testid'?: string;
};

// A change against the previous period: an arrow, a sign and the percent, so colour is never the only
// word. A change that rounds to zero is flat. Server-renderable: plain markup, HeroUI's chip classes.
export function TrendChip({
  change,
  isInverse = false,
  suffix,
  size = 'sm',
  className,
  'data-testid': testId,
}: TrendChipProps) {
  const known = Number.isFinite(change);
  const percent = known ? formatChange(change) : '';
  const flat = !known || Math.round(Math.abs(change) * 1000) === 0;
  const trend: Trend = flat ? 'flat' : change > 0 ? 'up' : 'down';
  const good = (trend === 'up') !== isInverse;
  const tone = flat ? 'neutral' : good ? 'success' : 'danger';
  const sign = trend === 'up' ? '+' : trend === 'down' ? '−' : '';
  const shown = known ? `${sign}${percent}` : '—';
  const heard = !known
    ? t.trend.none
    : trend === 'up'
      ? t.trend.up(percent)
      : trend === 'down'
        ? t.trend.down(percent)
        : t.trend.flat;
  const Arrow = ARROWS[trend];
  const slots = chipVariants({ variant: 'soft', size });
  return (
    <span
      className={['inline-flex items-center gap-1.5', className]
        .filter(Boolean)
        .join(' ')}
      data-testid={testId}
    >
      <span
        data-slot="trend-chip"
        data-trend={trend}
        data-tone={tone}
        className={slots.base({ className: trendChip({ tone }) })}
      >
        <span aria-hidden className="inline-flex shrink-0">
          <Arrow />
        </span>
        <span aria-hidden dir="ltr" className={`${slots.label()} tabular-nums`}>
          {shown}
        </span>
        <span className="sr-only">{heard}</span>
      </span>
      {suffix ? <span className="text-xs text-muted">{suffix}</span> : null}
    </span>
  );
}
