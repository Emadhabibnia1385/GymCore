import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Button, EmptyState, ErrorState, PageHeader, PageSkeleton, StatusChip, Tabs, type StatusTone } from "@nyxon/nasim";
import { useState } from "react";
import { formatNumber } from "@/shared/format";
import { TINT, tintStyle } from "@/shared/personColor";
import { fill, t } from "@/strings";
import { dayQuery, type DayRow } from "./api";
import { OutcomeButtons } from "./OutcomeButtons";
import { OutcomeSheet, type Target } from "./OutcomeSheet";
import { SheetView } from "./SheetView";

const a = t.attend;
const TONES: Record<string, StatusTone> = { PRESENT: "success", ABSENT_UNAUTHORIZED: "danger", ABSENT_ALLOWED: "info", COACH_CANCELLED: "info", HOLIDAY: "neutral" };
const DAY = 24 * 3600 * 1000;
const SHORT = ["ش", "ی", "د", "س", "چ", "پ", "ج"] as const; // the week from Saturday
/** The same weekday, `weeks` weeks away. */
function shiftWeeks(iso: string, weeks: number): string {
	const moved = new Date(new Date(`${iso}T12:00:00`).getTime() + weeks * 7 * DAY);
	return `${moved.getFullYear()}-${String(moved.getMonth() + 1).padStart(2, "0")}-${String(moved.getDate()).padStart(2, "0")}`;
}
const persianDay = new Intl.DateTimeFormat("fa-IR-u-ca-persian", { day: "numeric" });
const weekdayName = new Intl.DateTimeFormat("fa-IR", { weekday: "short" });

/** The seven days (Saturday first) of the week that holds `iso`. */
function weekOf(iso: string) {
	const noon = new Date(`${iso}T12:00:00`);
	const start = new Date(noon.getTime() - ((noon.getDay() + 1) % 7) * DAY);
	return Array.from({ length: 7 }, (_, index) => {
		const day = new Date(start.getTime() + index * DAY);
		const stamp = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
		return { iso: stamp, label: persianDay.format(day), name: weekdayName.format(day), short: SHORT[index], friday: index === 6 };
	});
}

export function AttendancePage() {
	return (
		<div className="flex flex-col gap-4">
			<PageHeader title={a.title} description={a.hint} />
			<Tabs
				label={a.title}
				items={[
					{ id: "day", label: a.tabDay, content: <DayView /> },
					{ id: "month", label: a.tabMonth, content: <SheetView /> },
				]}
			/>
		</div>
	);
}

function DayView() {
	const [iso, setIso] = useState<string | null>(null);
	const [target, setTarget] = useState<Target | null>(null);
	const { data, isPending, isError, refetch } = useQuery({ ...dayQuery(iso), placeholderData: keepPreviousData });
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;

	const done = data.rows.filter((row) => row.status !== null).length;
	const open = (row: DayRow) => setTarget({ courseId: row.course_id, iso: data.iso, title: row.student, subtitle: `${row.class_title}${row.time ? ` · ${row.time}` : ""} · ${data.label}`, current: row.status ? row.label : a.pending, isFuture: data.is_future });

	return (
		<div className="flex flex-col gap-4">
			{/* The week is its own full-width row so seven days never fight the buttons for room. */}
			<ul className="grid grid-cols-7 gap-1 sm:gap-2" aria-label={a.week}>
				{weekOf(data.iso).map((day) => (
					<li key={day.iso} className="min-w-0">
						<button
							type="button"
							aria-current={day.iso === data.iso ? "date" : undefined}
							aria-label={`${day.name} ${day.label}`}
							onClick={() => setIso(day.iso)}
							className={`flex w-full flex-col items-center rounded-field border py-1.5 outline-none focus-visible:ring-2 focus-visible:ring-accent sm:py-2 ${day.iso === data.iso ? "border-accent bg-accent text-accent-foreground" : day.friday ? "border-border bg-danger/10" : "border-border bg-surface hover:bg-surface-secondary"}`}
						>
							<span className="text-[11px] opacity-80 sm:text-xs"><span className="sm:hidden">{day.short}</span><span className="hidden sm:inline">{day.name}</span></span>
							<span className="text-base font-semibold tabular-nums">{day.label}</span>
						</button>
					</li>
				))}
			</ul>
			<div className="grid grid-cols-3 gap-2">
				<Button variant="secondary" size="sm" onPress={() => setIso(shiftWeeks(data.iso, -1))}>{`› ${a.prevWeek}`}</Button>
				<Button variant={data.is_today ? "primary" : "secondary"} size="sm" onPress={() => setIso(null)}>{t.common.today}</Button>
				<Button variant="secondary" size="sm" onPress={() => setIso(shiftWeeks(data.iso, 1))}>{`${a.nextWeek} ‹`}</Button>
			</div>

			<div className="flex flex-wrap items-center justify-between gap-2">
				<h2 className="font-semibold">{data.label}</h2>
				{data.rows.length > 0 ? <span className="text-sm text-muted">{fill(a.summary, { done: formatNumber(done), total: formatNumber(data.rows.length) })}</span> : null}
			</div>

			{data.rows.length === 0 ? (
				<EmptyState title={a.none} description={a.noneHint} />
			) : (
				<ul className="grid grid-cols-1 gap-3 md:grid-cols-2 2xl:grid-cols-3">
					{data.rows.map((row) => (
						<li key={row.course_id} style={tintStyle(row.course_id)} className="flex flex-col gap-3 rounded-box border border-border bg-surface p-3">
							<div className="flex items-start justify-between gap-2">
								<span className="flex min-w-0 items-center gap-2">
									<span className={`rounded-field px-2 py-1 text-xs font-semibold tabular-nums ${TINT}`}>{row.time || "—"}</span>
									<span className="flex min-w-0 flex-col">
										<span className="truncate font-medium">{row.student}</span>
										<span className="truncate text-xs text-muted">{row.class_title}</span>
									</span>
								</span>
								<StatusChip size="sm" tone={row.status ? (TONES[row.status] ?? "neutral") : "neutral"} label={row.status ? row.label : a.pending} />
							</div>
							<OutcomeButtons row={row} iso={data.iso} isFuture={data.is_future} onMore={() => open(row)} />
						</li>
					))}
				</ul>
			)}
			<OutcomeSheet target={target} onClose={() => setTarget(null)} />
		</div>
	);
}
