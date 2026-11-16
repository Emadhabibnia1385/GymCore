// Written out, not built from the tone name: Tailwind only keeps class names it can read. The neutral
// tone is for the series a chart compares with (the previous period), so it recedes behind the main one.
export const SERIES_TONES = {
  accent: {
    stroke: 'stroke-accent',
    fill: 'fill-accent/15',
    bg: 'bg-accent',
    swatch: 'text-accent',
  },
  success: {
    stroke: 'stroke-success',
    fill: 'fill-success/15',
    bg: 'bg-success',
    swatch: 'text-success',
  },
  info: {
    stroke: 'stroke-info',
    fill: 'fill-info/15',
    bg: 'bg-info',
    swatch: 'text-info',
  },
  neutral: {
    stroke: 'stroke-muted',
    fill: 'fill-muted/10',
    bg: 'bg-muted',
    swatch: 'text-muted',
  },
} as const;

export type SeriesTone = keyof typeof SERIES_TONES;
