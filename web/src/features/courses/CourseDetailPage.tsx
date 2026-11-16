import { useQuery } from "@tanstack/react-query";
import { ErrorState, PageHeader, PageSkeleton, SectionCard, StaticTable, StatusChip, type StatusTone } from "@nyxon/nasim";
import { useState } from "react";
import { OutcomeSheet, type Target } from "@/features/attendance";
import { CourseActions } from "@/features/manage";
import { isoDay } from "@/shared/DatePick";
import { fill, t } from "@/strings";
import { courseQuery, type Slot } from "./api";
import { CourseSummaryCard } from "./CourseSummaryCard";

const c = t.course;
const TONES: Record<string, StatusTone> = {
	PRESENT: "success",
	ABSENT_UNAUTHORIZED: "danger",
	ABSENT_ALLOWED: "info",
	COACH_CANCELLED: "info",
	HOLIDAY: "neutral",
	MOVED: "info",
};

function outcomeLabel(slot: Slot) {
	return slot.session_no ? `${slot.label} · ${fill(c.sessionNo, { n: slot.session_no })}` : slot.label;
}

function Outcome({ slot }: { slot: Slot }) {
	return <StatusChip size="sm" tone={slot.status ? (TONES[slot.status] ?? "neutral") : "neutral"} label={outcomeLabel(slot)} />;
}

export function CourseDetailPage({ role, id, backHref }: { role: "admin" | "student"; id: number; backHref: string }) {
	const { data, isPending, isError, refetch } = useQuery(courseQuery(role, id));
	const [target, setTarget] = useState<Target | null>(null);
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;
	const coach = role === "admin";
	const today = isoDay(0);

	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={data.class_title} description={coach ? data.client_name : undefined} backHref={backHref} />
			<CourseSummaryCard course={data} />
			{coach ? (
				<SectionCard title={t.manage.courseStatus}>
					<CourseActions course={data} />
				</SectionCard>
			) : null}
			<SectionCard title={c.grid} description={coach ? t.attend.hint : undefined}>
				{coach ? (
					<ul className="flex flex-col gap-2">
						{data.slots.map((slot) => (
							<li key={slot.iso}>
								<button
									type="button"
									className="flex min-h-12 w-full items-center justify-between gap-3 rounded-field border border-border bg-surface px-4 py-2 text-start outline-none hover:bg-surface-secondary focus-visible:ring-2 focus-visible:ring-accent"
									onClick={() => setTarget({ courseId: data.id, iso: slot.iso, title: data.client_name, subtitle: `${data.class_title} · ${slot.weekday} ${slot.date}`, current: slot.status ? slot.label : t.attend.pending, isFuture: slot.iso > today })}
								>
									<span>{`${slot.weekday} ${slot.date}`}</span>
									<Outcome slot={slot} />
								</button>
							</li>
						))}
					</ul>
				) : (
					<StaticTable caption={c.gridCaption} columns={[c.date, c.outcome]} rows={data.slots.map((slot, index) => ({ id: String(index), cells: [`${slot.weekday} ${slot.date}`, <Outcome key="o" slot={slot} />] }))} />
				)}
			</SectionCard>
			{coach ? <OutcomeSheet target={target} onClose={() => setTarget(null)} /> : null}
		</div>
	);
}
