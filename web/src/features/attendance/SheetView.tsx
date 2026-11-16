import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Button, EmptyState, ErrorState, PageSkeleton } from "@nyxon/nasim";
import { useState } from "react";
import { formatNumber } from "@/shared/format";
import { TINT, tintStyle } from "@/shared/personColor";
import { t } from "@/strings";
import { sheetQuery, type SheetCell } from "./api";
import { OutcomeSheet, type Target } from "./OutcomeSheet";

const a = t.attend;

// What a cell says, in as few characters as a table column can hold.
const SHORT: Record<string, string> = {
	ABSENT_UNAUTHORIZED: a.short.absent,
	ABSENT_ALLOWED: a.short.allowed,
	COACH_CANCELLED: a.short.cancelled,
	HOLIDAY: a.short.holiday,
	MOVED: a.short.moved,
};
const TONE: Record<string, string> = {
	PRESENT: "bg-success/20 text-success",
	ABSENT_UNAUTHORIZED: "bg-danger/20 text-danger",
	ABSENT_ALLOWED: "bg-warning/20 text-warning",
	COACH_CANCELLED: "bg-info/20 text-info",
	HOLIDAY: "bg-surface-secondary text-muted",
	MOVED: "bg-info/20 text-info",
};

function label(cell: SheetCell): string {
	if (cell.status === "PRESENT") return cell.session_no ? formatNumber(cell.session_no) : a.short.present;
	if (cell.status) return SHORT[cell.status] ?? "";
	return "·";
}

/** A whole month on one page: a row per day, a column per student, like the coach's own sheet. */
export function SheetView() {
	const [month, setMonth] = useState<[number, number] | null>(null);
	const [target, setTarget] = useState<Target | null>(null);
	const { data, isPending, isError, refetch } = useQuery({ ...sheetQuery(month), placeholderData: keepPreviousData });
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;
	const today = data.days.find((day) => day.today)?.iso ?? "";

	return (
		<div className="flex flex-col gap-3">
			<div className="flex items-center justify-between gap-2">
				<Button size="sm" variant="secondary" onPress={() => setMonth(data.prev)}>{t.money.prevMonth}</Button>
				<span className="font-semibold">{data.label}</span>
				{data.next ? <Button size="sm" variant="secondary" onPress={() => setMonth(data.next)}>{t.money.nextMonth}</Button> : <span className="w-20" />}
			</div>
			<ul className="flex flex-wrap gap-2 text-xs text-muted" aria-label={a.legend}>
				{Object.entries({ PRESENT: a.short.presentWord, ABSENT_UNAUTHORIZED: a.short.absentWord, ABSENT_ALLOWED: a.short.allowedWord, COACH_CANCELLED: a.short.cancelledWord, HOLIDAY: a.short.holidayWord }).map(([status, word]) => (
					<li key={status} className={`rounded-full px-2 py-0.5 ${TONE[status]}`}>{word}</li>
				))}
				<li className="rounded-full bg-accent/20 px-2 py-0.5 text-accent">{a.short.paidWord}</li>
			</ul>
			{data.columns.length === 0 ? (
				<EmptyState title={a.sheetNone} />
			) : (
				<div className="max-h-[70vh] overflow-auto rounded-box border border-border">
					<table className="w-full border-collapse text-center text-sm">
						<thead>
							<tr>
								<th scope="col" className="sticky end-0 top-0 z-20 min-w-24 bg-surface-secondary p-2">{a.dateCol}</th>
								{data.columns.map((column) => (
									<th key={column.course_id} scope="col" className="sticky top-0 z-10 min-w-28 border-s border-border bg-surface-secondary p-1.5 font-normal">
										<span style={tintStyle(column.course_id)} className={`block rounded-field px-2 py-1 text-xs font-semibold ${TINT}`}>{column.student}</span>
										<span className="text-[11px] text-muted">{column.class_title}</span>
									</th>
								))}
							</tr>
						</thead>
						<tbody>
							{data.days.map((day) => (
								<tr key={day.iso} className={`border-t border-border ${day.friday ? "bg-danger/15" : day.today ? "bg-accent/10" : ""}`}>
									<th scope="row" className={`sticky end-0 z-10 p-1.5 text-start font-normal ${day.friday ? "bg-danger/20" : day.today ? "bg-accent/20" : "bg-surface"}`}>
										<span className="font-medium tabular-nums">{formatNumber(day.day)}</span> <span className="text-xs text-muted">{day.weekday}</span>
									</th>
									{data.columns.map((column) => {
										const cell = data.cells[String(column.course_id)]?.[day.iso];
										if (!cell) return <td key={column.course_id} className="border-s border-border" />;
										const body = (
											<span className={`inline-flex min-h-7 min-w-12 items-center justify-center gap-1 rounded-field px-1.5 text-xs font-semibold ${cell.status ? TONE[cell.status] : "text-muted"}`}>
												{label(cell)}
												{cell.paid ? <span className="rounded bg-accent px-1 text-[10px] text-accent-foreground">{a.short.paid}</span> : null}
											</span>
										);
										return (
											<td key={column.course_id} className="border-s border-border p-0.5">
												<button
													type="button"
													className="rounded-field outline-none focus-visible:ring-2 focus-visible:ring-accent"
													onClick={() => setTarget({ courseId: column.course_id, iso: day.iso, title: column.student, subtitle: `${column.class_title} · ${day.weekday} ${formatNumber(day.day)} ${data.label}`, current: cell.status ? label(cell) : a.pending, isFuture: day.iso > today })}
												>
													{body}
												</button>
											</td>
										);
									})}
								</tr>
							))}
						</tbody>
					</table>
				</div>
			)}
			<OutcomeSheet target={target} onClose={() => setTarget(null)} />
		</div>
	);
}
