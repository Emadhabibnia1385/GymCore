import { useState } from 'react';
import {
  AreaChart,
  DateRangeField,
  type DateRangePreset,
  type DateRangeValue,
  Sparkline,
  StatCard,
  TrendChip,
} from '..';
import { Section } from './PrimitivesDemo';

// Sample figures for the charts and key numbers; the copy and the data live in this file.
const DAYS = 30;
const number = new Intl.NumberFormat('fa-IR');
const toman = (value: number) => `${number.format(value)} تومان`;

const sales = Array.from({ length: DAYS }, (_, day) =>
  Math.round(
    (2.2 +
      Math.sin(day / 3.2) * 0.8 +
      day * 0.045 +
      (day % 5 === 0 ? 0.5 : 0)) *
      1_000_000,
  ),
);
const orders = Array.from({ length: DAYS }, (_, day) =>
  Math.round(28 + Math.cos(day / 2.6) * 9 + day * 0.7),
);
// A day with no observation is a gap, not a zero.
const newUsers = Array.from({ length: DAYS }, (_, day): number | null =>
  day === 12 || day === 13 ? null : Math.round(9 + Math.sin(day / 1.9) * 4),
);
// The month before, for the line this one is compared with.
const lastMonth = sales.map((value, day) =>
  Math.round(value * (0.82 + Math.sin(day / 2.1) * 0.06)),
);
const refunds = Array.from({ length: DAYS }, (_, day) =>
  Math.round(6 - day * 0.09 + Math.sin(day) * 1.2),
);

const dayTitle = (day: number) => `${number.format(day + 1)} مهر ۱۴۰۵`;
const TICKS = Array.from({ length: DAYS }, (_, day) => ({
  key: `d${day}`,
  label: day % 7 === 0 ? `${number.format(day + 1)} مهر` : '',
  title: dayTitle(day),
}));

const last = (list: readonly (number | null)[]) =>
  list.filter((value): value is number => value !== null).at(-1)!;

const KPIS = [
  {
    label: 'فروش موفق',
    value: toman(sales.reduce((sum, value) => sum + value, 0)),
    change: 0.124,
    data: sales,
    summary: `روند فروش ۳۰ روز گذشته؛ امروز ${toman(last(sales))}`,
    tone: 'accent',
    isInverse: false,
  },
  {
    label: 'سفارش‌ها',
    value: `${number.format(orders.reduce((sum, value) => sum + value, 0))} سفارش`,
    change: 0.041,
    data: orders,
    summary: `روند سفارش‌ها؛ امروز ${number.format(last(orders))} سفارش`,
    tone: 'info',
    isInverse: false,
  },
  {
    label: 'بازگشت وجه',
    value: `${number.format(refunds.reduce((sum, value) => sum + value, 0))} مورد`,
    change: -0.083,
    data: refunds,
    summary: `روند بازگشت وجه؛ امروز ${number.format(last(refunds))} مورد`,
    tone: 'success',
    isInverse: true,
  },
  {
    label: 'کاربران جدید',
    value: `${number.format(newUsers.reduce<number>((sum, value) => sum + (value ?? 0), 0))} نفر`,
    change: 0,
    data: newUsers,
    summary: 'روند ثبت‌نام؛ دو روز داده ثبت نشده است',
    tone: 'accent',
    isInverse: false,
  },
] as const;

const Y_TICKS = [0, 2_000_000, 4_000_000, 6_000_000].map((value) => ({
  value,
  label: value === 0 ? '۰' : `${number.format(value / 1_000_000)} م`,
}));

// Today in this sample is 8 Aban 1405 (2026-10-30); a real screen works its presets out from the date.
const PRESETS: DateRangePreset[] = [
  { id: 'today', label: 'امروز', start: '2026-10-30', end: '2026-10-30' },
  { id: 'week', label: '۷ روز', start: '2026-10-24', end: '2026-10-30' },
  { id: 'days30', label: '۳۰ روز', start: '2026-10-01', end: '2026-10-30' },
  { id: 'month', label: 'این ماه', start: '2026-10-23', end: '2026-10-30' },
];

// The key figures of a sales dashboard and its time series, on sample data.
export function AnalyticsDemo() {
  const [period, setPeriod] = useState<DateRangeValue>(PRESETS[2]!);
  return (
    <Section title="آمار و نمودار">
      <DateRangeField
        label="بازهٔ گزارش"
        description="روزهای گزارش را از تقویم یا از بازه‌های آماده انتخاب کنید."
        value={period}
        onChange={setPeriod}
        calendarLabel="تقویم بازهٔ گزارش"
        clearLabel="پاک کردن"
        presets={PRESETS}
        presetsLabel="بازه‌های آماده"
      />
      <div className="grid gap-3 sm:grid-cols-2">
        {KPIS.map((kpi) => (
          <StatCard
            key={kpi.label}
            label={kpi.label}
            value={kpi.value}
            hint="۳۰ روز گذشته"
            trend={
              <TrendChip
                change={kpi.change}
                isInverse={kpi.isInverse}
                suffix="نسبت به ماه قبل"
              />
            }
            sparkline={
              <Sparkline
                data={kpi.data}
                summary={kpi.summary}
                tone={kpi.tone}
              />
            }
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-3">
        <TrendChip change={0.12} />
        <TrendChip change={-0.034} />
        <TrendChip change={-0.05} isInverse />
        <TrendChip change={0.05} isInverse />
        <TrendChip change={0} />
        <TrendChip change={0.12} size="md" suffix="نسبت به هفته قبل" />
      </div>
      <div className="rounded-2xl border border-border bg-surface p-4 shadow-surface sm:p-5">
        <AreaChart
          data-testid="area-demo"
          title="فروش روزانه نسبت به ماه قبل"
          summary={`۳۰ روز؛ بیشترین فروش ${toman(Math.max(...sales))}؛ امروز ${toman(last(sales))} و ماه قبل ${toman(last(lastMonth))}.`}
          showSummary
          ticks={TICKS}
          series={[
            {
              key: 'sales',
              label: 'این ماه',
              points: sales.map((value) => ({ value, text: toman(value) })),
            },
            {
              key: 'last',
              label: 'ماه قبل',
              points: lastMonth.map((value) => ({ value, text: toman(value) })),
            },
          ]}
          yTicks={Y_TICKS}
          empty="در این بازه فروشی ثبت نشده است."
          table={{
            showLabel: 'نمایش جدول مقدارها',
            label: 'جدول فروش روزانه',
            stepHeader: 'روز',
          }}
        />
      </div>
      <div className="rounded-2xl border border-border bg-surface p-4 shadow-surface sm:p-5">
        <AreaChart
          title="فروش یک هفته"
          summary="هفت روز؛ بیشترین فروش در روز پنجم."
          ticks={TICKS.slice(0, 7).map((tick, day) => ({
            ...tick,
            label: number.format(day + 1),
          }))}
          series={[
            {
              key: 'sales',
              label: 'فروش',
              tone: 'success',
              points: sales
                .slice(0, 7)
                .map((value) => ({ value, text: toman(value) })),
            },
          ]}
          empty="فروشی ثبت نشده است."
          table={{
            showLabel: 'نمایش جدول مقدارها',
            label: 'جدول فروش هفته',
            stepHeader: 'روز',
          }}
        />
      </div>
    </Section>
  );
}
