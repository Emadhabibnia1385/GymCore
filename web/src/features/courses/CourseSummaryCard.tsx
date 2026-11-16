import { KeyValueList, SectionCard, StatusChip, type StatusTone, UsageBar } from "@nyxon/nasim";
import { formatNumber } from "@/shared/format";
import { fill, t } from "@/strings";
import type { CourseSummary } from "./api";

const c = t.course;
const TONES: Record<CourseSummary["status"], StatusTone> = { ACTIVE: "success", FINISHED: "neutral", PAUSED: "warning" };

export function CourseSummaryCard({ course, level = 2 }: { course: CourseSummary; level?: 2 | 3 }) {
	const allowance =
		course.allowed_absence > 0
			? fill(c.allowanceOf, { used: formatNumber(course.absent_allowed), max: formatNumber(course.allowed_absence) })
			: fill(c.allowanceFree, { used: formatNumber(course.absent_allowed) });
	return (
		<SectionCard title={course.class_title} level={level} actions={<StatusChip tone={TONES[course.status]} label={course.status_label} />}>
			<div className="flex flex-col gap-4">
				<UsageBar
					label={c.sessions}
					used={course.consumed}
					total={course.total}
					valueText={fill(c.used, { used: formatNumber(course.consumed), total: formatNumber(course.total) })}
				/>
				<KeyValueList
					layout="grid"
					items={[
						{ label: c.remainingLabel, value: formatNumber(course.remaining), numeric: true },
						{ label: c.start, value: course.start, numeric: true },
						{ label: c.days, value: course.schedule },
						{ label: c.allowance, value: allowance },
						{ label: c.unauthorized, value: formatNumber(course.absent_unauthorized), numeric: true },
					]}
				/>
			</div>
		</SectionCard>
	);
}
