'use client';

import { Label, Meter } from '@heroui/react';
import { tv } from 'tailwind-variants';
import { DangerIcon, ErrorIcon } from '../icons';
import { t } from '../strings';

type UsageTone = 'normal' | 'warning' | 'danger' | 'unlimited';

const usageBar = tv({
  slots: {
    root: 'min-w-0 gap-x-3 gap-y-1.5',
    label: 'min-w-0 text-sm font-medium text-foreground',
    output: 'flex items-center justify-end gap-1.5 text-sm text-foreground',
    track: '',
    icon: 'shrink-0',
    infinity: 'text-muted',
  },
  variants: {
    // The fill is a meaning (how full, how bad): each colour holds 3:1 on the track and the surface.
    tone: {
      normal: { root: '[--meter-fill:var(--accent)]' },
      warning: {
        root: '[--meter-fill:var(--warning-soft-foreground)]',
        icon: 'text-warning-soft-foreground',
      },
      danger: { root: '[--meter-fill:var(--danger)]', icon: 'text-danger' },
      unlimited: { root: '[--meter-fill:var(--muted)]' },
    },
    size: {
      regular: {},
      // One line: the track takes what the value text leaves, the label is for a screen reader.
      compact: {
        root: 'flex items-center gap-x-2',
        label: 'sr-only',
        output: 'order-last shrink-0 text-xs',
        track: 'order-first min-w-12 flex-1',
      },
    },
  },
  defaultVariants: { tone: 'normal', size: 'regular' },
});

// The fill token of each tone, for the contrast test: the same names the classes above carry.
export const USAGE_TONES = {
  normal: 'accent',
  warning: 'warning-soft-foreground',
  danger: 'danger',
  unlimited: 'muted',
} as const satisfies Record<UsageTone, string>;

type UsageBarProps = {
  /** What is metered («مصرف داده»): names the meter, and is on screen unless `size` is `"compact"`. */
  label: string;
  /** How much is used, in the unit of `total`. */
  used: number;
  /** The allowance in that unit; `null` is unlimited (an infinity sign and a neutral, full bar). */
  total: number | null;
  /** The figures as the app formats them (bytes, days): «۸٫۲ از ۱۰ گیگابایت». It is the meter's text too. */
  valueText: string;
  /** From this percent of the total the bar warns. Default 80. */
  warningAt?: number;
  /** From this percent of the total it is danger. Default 100. */
  dangerAt?: number;
  size?: 'regular' | 'compact';
  className?: string;
  'data-testid'?: string;
};

function toneOf(
  used: number,
  total: number | null,
  warningAt: number,
  dangerAt: number,
): UsageTone {
  if (total === null) return 'unlimited';
  // With nothing allowed, anything used is over the limit
  const percent = total > 0 ? (used / total) * 100 : used > 0 ? Infinity : 0;
  if (percent >= dangerAt) return 'danger';
  return percent >= warningAt ? 'warning' : 'normal';
}

// How much of an allowance is used: a bar, the figures in the app's words and a status that is also an
// icon and, to a screen reader, words. Built on HeroUI's Meter (role meter, aria-valuetext).
export function UsageBar({
  label,
  used,
  total,
  valueText,
  warningAt = 80,
  dangerAt = 100,
  size = 'regular',
  className,
  'data-testid': testId,
}: UsageBarProps) {
  const tone = toneOf(Math.max(0, used), total, warningAt, dangerAt);
  const slots = usageBar({ tone, size });
  // An unlimited bar is full: its range is what is used, and 1 when nothing is.
  const max = total === null ? Math.max(used, 1) : total > 0 ? total : 1;
  const value =
    total === null
      ? max
      : total > 0
        ? Math.min(Math.max(used, 0), total)
        : used > 0
          ? 1
          : 0;
  const words =
    tone === 'warning'
      ? t.usageBar.warning
      : tone === 'danger'
        ? t.usageBar.danger
        : tone === 'unlimited'
          ? t.usageBar.unlimited
          : undefined;
  return (
    <Meter
      value={value}
      minValue={0}
      maxValue={max}
      size={size === 'compact' ? 'sm' : 'md'}
      valueLabel={words ? `${valueText}، ${words}` : valueText}
      className={slots.root({ className })}
      data-tone={tone}
      data-size={size}
      data-testid={testId}
    >
      <Label className={slots.label()}>{label}</Label>
      <Meter.Output className={slots.output()}>
        {tone === 'warning' || tone === 'danger' ? (
          <span aria-hidden data-slot="usage-status" className={slots.icon()}>
            {tone === 'danger' ? <DangerIcon /> : <ErrorIcon />}
          </span>
        ) : null}
        <span className="tabular-nums">{valueText}</span>
        {tone === 'unlimited' ? (
          <span aria-hidden className={slots.infinity()}>
            ∞
          </span>
        ) : null}
      </Meter.Output>
      <Meter.Track className={slots.track()}>
        <Meter.Fill />
      </Meter.Track>
    </Meter>
  );
}
