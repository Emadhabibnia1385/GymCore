import { Button, SelectField } from "@nyxon/nasim";
import { ScrollChips } from "@/shared/ScrollChips";
import { DatePick } from "@/shared/DatePick";
import { formatNumber } from "@/shared/format";
import { t } from "@/strings";
import type { Period, PeriodQuery } from "./api";

const m = t.money;
export type Mode = "month" | "year" | "last30" | "last90" | "range";

const MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"];

/** Which stretch of days to look at: a month, a year, the last weeks, or any two dates. */
export function PeriodBar({ mode, onMode, data, query, onQuery }: { mode: Mode; onMode: (mode: Mode) => void; data: Period; query: PeriodQuery; onQuery: (query: PeriodQuery) => void }) {
	const years = Array.from({ length: 6 }, (_, index) => data.jy - index);
	const jy = query.jy ?? data.jy;
	return (
		<div className="flex flex-col gap-3 rounded-box border border-border bg-surface p-3">
			<ScrollChips
				inset="card"
				label={m.period}
				value={mode}
				onChange={(value) => {
					const next = value as Mode;
					onMode(next);
					if (next === "month") onQuery({});
					if (next === "year") onQuery({ jy: data.jy });
					if (next === "last30") onQuery({ last: 30 });
					if (next === "last90") onQuery({ last: 90 });
					if (next === "range") onQuery({ start: data.start, end: data.end });
				}}
				options={[
					{ value: "month", label: m.pMonth },
					{ value: "year", label: m.pYear },
					{ value: "last30", label: m.pLast30 },
					{ value: "last90", label: m.pLast90 },
					{ value: "range", label: m.pRange },
				]}
			/>

			{mode === "month" ? (
				<div className="flex flex-col gap-2 sm:flex-row sm:items-end">
					<div className="grid min-w-0 grid-cols-2 gap-2 sm:order-2 sm:flex-1">
						<SelectField label={m.pickMonth} value={String(query.jm ?? data.jm)} onChange={(value) => value && onQuery({ jy, jm: Number(value) })} options={MONTHS.map((name, index) => ({ value: String(index + 1), label: name }))} />
						<SelectField label={m.pickYear} value={String(jy)} onChange={(value) => value && onQuery({ jy: Number(value), jm: query.jm ?? data.jm })} options={years.map((year) => ({ value: String(year), label: formatNumber(year).replace(/٬/g, "") }))} />
					</div>
					<div className="grid grid-cols-2 gap-2 sm:contents">
						<Button size="sm" variant="secondary" className="sm:order-1" isDisabled={!data.prev_month} onPress={() => data.prev_month && onQuery({ jy: data.prev_month[0], jm: data.prev_month[1] })}>{m.prevMonth}</Button>
						<Button size="sm" variant="secondary" className="sm:order-3" isDisabled={!data.next_month} onPress={() => data.next_month && onQuery({ jy: data.next_month[0], jm: data.next_month[1] })}>{m.nextMonth}</Button>
					</div>
				</div>
			) : null}

			{mode === "year" ? (
				<div className="max-w-60">
					<SelectField label={m.pickYear} value={String(jy)} onChange={(value) => value && onQuery({ jy: Number(value) })} options={years.map((year) => ({ value: String(year), label: formatNumber(year).replace(/٬/g, "") }))} />
				</div>
			) : null}

			{mode === "range" ? (
				<div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
					<DatePick label={m.from} value={query.start ?? data.start} shortcuts={false} onChange={(iso) => iso && onQuery({ start: iso, end: query.end ?? data.end })} />
					<DatePick label={m.to} value={query.end ?? data.end} shortcuts={false} onChange={(iso) => iso && onQuery({ start: query.start ?? data.start, end: iso })} />
				</div>
			) : null}
		</div>
	);
}
