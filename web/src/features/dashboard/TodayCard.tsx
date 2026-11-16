import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { Button, EmptyState, Notice, SectionCard, StatusChip, type StatusTone } from "@nyxon/nasim";
import { useState } from "react";
import { dayQuery, OutcomeSheet, recordAttendance, type DayRow, type Target } from "@/features/attendance";
import { formatNumber } from "@/shared/format";
import { TINT, tintStyle } from "@/shared/personColor";
import { fill, t } from "@/strings";

const d = t.dashboard;
const TONES: Record<string, StatusTone> = { PRESENT: "success", ABSENT_UNAUTHORIZED: "danger", ABSENT_ALLOWED: "info", COACH_CANCELLED: "info", HOLIDAY: "neutral" };

/** Today's classes with the attendance buttons right there: most days the coach never leaves this card. */
export function TodayCard() {
	const queryClient = useQueryClient();
	const { data } = useQuery(dayQuery(null));
	const [target, setTarget] = useState<Target | null>(null);
	const quick = useMutation({
		mutationFn: ({ row, status }: { row: DayRow; status: string }) => recordAttendance({ course_id: row.course_id, date: data!.iso, status }),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin"] }),
	});
	const rows = data?.rows ?? [];
	const done = rows.filter((row) => row.status !== null).length;

	return (
		<SectionCard
			title={d.todayTitle}
			description={rows.length > 0 ? fill(t.attend.summary, { done: formatNumber(done), total: formatNumber(rows.length) }) : undefined}
			actions={<Link to="/attendance" className="text-sm text-accent underline">{d.openAttendance}</Link>}
		>
			{quick.isError ? <Notice tone="danger" role="alert">{quick.error.message}</Notice> : null}
			{rows.length === 0 ? (
				<EmptyState title={d.todayNone} />
			) : (
				<ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
					{rows.map((row) => (
						<li key={row.course_id} style={tintStyle(row.course_id)} className="flex flex-col gap-3 rounded-box border border-border bg-surface-secondary/40 p-3">
							<div className="flex items-start justify-between gap-2">
								<span className="flex min-w-0 items-center gap-2">
									<span className={`rounded-field px-2 py-1 text-xs font-semibold tabular-nums ${TINT}`}>{row.time || "—"}</span>
									<span className="flex min-w-0 flex-col">
										<span className="truncate font-medium">{row.student}</span>
										<span className="truncate text-xs text-muted">{row.class_title}</span>
									</span>
								</span>
								<StatusChip size="sm" tone={row.status ? (TONES[row.status] ?? "neutral") : "neutral"} label={row.status ? row.label : t.attend.pending} />
							</div>
							<div className="grid grid-cols-3 gap-2">
								<Button size="sm" variant={row.status === "PRESENT" ? "primary" : "secondary"} isDisabled={quick.isPending} onPress={() => quick.mutate({ row, status: "PRESENT" })}>{t.attend.quickPresent}</Button>
								<Button size="sm" variant={row.status === "ABSENT_UNAUTHORIZED" ? "danger" : "danger-soft"} isDisabled={quick.isPending} onPress={() => quick.mutate({ row, status: "ABSENT_UNAUTHORIZED" })}>{t.attend.quickAbsent}</Button>
								<Button size="sm" variant="ghost" onPress={() => setTarget({ courseId: row.course_id, iso: data!.iso, title: row.student, subtitle: `${row.class_title}${row.time ? ` · ${row.time}` : ""} · ${data!.label}`, current: row.status ? row.label : t.attend.pending, isFuture: false })}>{t.attend.more}</Button>
							</div>
						</li>
					))}
				</ul>
			)}
			<OutcomeSheet target={target} onClose={() => setTarget(null)} />
		</SectionCard>
	);
}
