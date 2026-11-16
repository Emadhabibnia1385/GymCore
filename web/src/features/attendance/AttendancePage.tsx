import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Button, EmptyState, ErrorState, PageHeader, PageSkeleton, StatusChip, type StatusTone } from "@nyxon/nasim";
import { useState } from "react";
import { t } from "@/strings";
import { dayQuery } from "./api";
import { OutcomeSheet, type Target } from "./OutcomeSheet";

const a = t.attend;
const TONES: Record<string, StatusTone> = { PRESENT: "success", ABSENT_UNAUTHORIZED: "danger", ABSENT_ALLOWED: "info", COACH_CANCELLED: "info", HOLIDAY: "neutral" };

export function AttendancePage() {
	const [iso, setIso] = useState<string | null>(null);
	const [target, setTarget] = useState<Target | null>(null);
	const { data, isPending, isError, refetch } = useQuery({ ...dayQuery(iso), placeholderData: keepPreviousData });
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;

	return (
		<div className="flex flex-col gap-4">
			<PageHeader title={a.title} description={data.label} meta={<span className="text-sm text-muted">{a.hint}</span>} />
			<div className="flex items-center justify-between gap-2">
				<Button variant="secondary" size="sm" onPress={() => setIso(data.prev)}>{a.prev}</Button>
				<Button variant={data.is_today ? "primary" : "secondary"} size="sm" onPress={() => setIso(null)}>{t.common.today}</Button>
				<Button variant="secondary" size="sm" onPress={() => setIso(data.next)}>{a.next}</Button>
			</div>

			{data.rows.length === 0 ? (
				<EmptyState title={a.none} description={a.noneHint} />
			) : (
				<ul className="flex flex-col gap-2">
					{data.rows.map((row) => (
						<li key={row.course_id}>
							<button
								type="button"
								className="flex min-h-14 w-full items-center justify-between gap-3 rounded-field border border-border bg-surface p-4 text-start outline-none transition-colors hover:bg-surface-secondary focus-visible:ring-2 focus-visible:ring-accent"
								onClick={() => setTarget({ courseId: row.course_id, iso: data.iso, title: row.student, subtitle: `${row.class_title}${row.time ? ` · ${row.time}` : ""} · ${data.label}`, current: row.status ? row.label : a.pending, isFuture: data.is_future })}
							>
								<span className="flex min-w-0 flex-col">
									<span className="font-medium">{row.student}</span>
									<span className="text-xs text-muted">{`${row.class_title}${row.time ? ` · ${row.time}` : ""}`}</span>
								</span>
								<StatusChip size="sm" tone={row.status ? (TONES[row.status] ?? "neutral") : "neutral"} label={row.status ? row.label : a.pending} />
							</button>
						</li>
					))}
				</ul>
			)}
			<OutcomeSheet target={target} onClose={() => setTarget(null)} />
		</div>
	);
}
