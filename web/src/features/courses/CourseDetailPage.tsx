import { useQuery } from "@tanstack/react-query";
import { ErrorState, PageHeader, PageSkeleton, SectionCard, StaticTable, StatusChip, type StatusTone } from "@nyxon/nasim";
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

function outcome(slot: Slot) {
	const label = slot.session_no ? `${slot.label} · ${fill(c.sessionNo, { n: slot.session_no })}` : slot.label;
	return <StatusChip size="sm" tone={slot.status ? (TONES[slot.status] ?? "neutral") : "neutral"} label={label} />;
}

export function CourseDetailPage({ role, id, backHref }: { role: "admin" | "student"; id: number; backHref: string }) {
	const { data, isPending, isError, refetch } = useQuery(courseQuery(role, id));
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;
	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={data.class_title} backHref={backHref} />
			<CourseSummaryCard course={data} />
			<SectionCard title={c.grid}>
				<StaticTable
					caption={c.gridCaption}
					columns={[c.date, c.outcome]}
					rows={data.slots.map((slot, index) => ({
						id: String(index),
						cells: [`${slot.weekday} ${slot.date}`, outcome(slot)],
					}))}
				/>
			</SectionCard>
		</div>
	);
}
