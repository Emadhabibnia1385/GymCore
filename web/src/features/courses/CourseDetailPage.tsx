import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { EmptyState, ErrorState, KeyValueList, PageHeader, PageSkeleton, SectionCard, StatCard, StaticTable, StatusChip, UsageBar } from "@nyxon/nasim";
import { useState } from "react";
import { OutcomeSheet, type Target } from "@/features/attendance";
import { CourseActions } from "@/features/manage";
import { isoDay } from "@/shared/DatePick";
import { formatNumber, formatToman } from "@/shared/format";
import { fill, t } from "@/strings";
import { courseQuery, type CourseDetail, type Slot } from "./api";
import { SessionTiles } from "./SessionTiles";

const c = t.course;
const KIND: Record<string, string> = { TUITION: "شهریه", GYM_FEE: "ورودی باشگاه", OTHER: "سایر" };

export function CourseDetailPage({ role, id, backHref }: { role: "admin" | "student"; id: number; backHref: string }) {
	const { data, isPending, isError, refetch } = useQuery(courseQuery(role, id));
	const [target, setTarget] = useState<Target | null>(null);
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;

	if (role === "student") return <StudentView data={data} backHref={backHref} />;
	const today = isoDay(0);
	const open = (slot: Slot) => setTarget({ courseId: data.id, iso: slot.iso, title: data.client_name, subtitle: `${data.class_title} · ${slot.weekday} ${slot.date}`, current: slot.status ? slot.label : t.attend.pending, isFuture: slot.iso > today });
	const next = data.slots.find((slot) => slot.status === null && slot.iso >= today);

	return (
		<div className="flex flex-col gap-6">
			<PageHeader
				title={data.class_title}
				description={data.client_name}
				backHref={backHref}
				meta={<StatusChip size="sm" tone={data.status === "ACTIVE" ? "success" : data.status === "PAUSED" ? "warning" : "neutral"} label={data.status_label} />}
				actions={<Link to="/students/$id" params={{ id: String(data.client_id) }} className="text-sm text-accent underline">{c.studentProfile}</Link>}
			/>

			<div className="grid grid-cols-1 gap-3 min-[480px]:grid-cols-2 xl:grid-cols-4">
				<StatCard label={c.remainingLabel} value={formatNumber(data.remaining)} hint={fill(c.used, { used: formatNumber(data.consumed), total: formatNumber(data.total) })} />
				<StatCard label={c.nextSession} value={next ? `${next.weekday} ${next.date}` : "—"} hint={data.schedule} />
				<StatCard label={c.paid} value={formatToman(data.paid ?? 0)} hint={fill(c.ofTotal, { total: formatToman((data.tuition ?? 0) + (data.gym_fee ?? 0)) })} />
				<StatCard label={c.outstanding} value={(data.outstanding ?? 0) > 0 ? formatToman(data.outstanding ?? 0) : c.settled} />
			</div>

			<div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-3">
				<div className="min-w-0 xl:col-span-2">
					<SectionCard title={c.grid} description={t.attend.hint}>
						<div className="flex flex-col gap-4">
							<UsageBar warningAt={101} dangerAt={101} label={c.sessions} used={data.consumed} total={data.total} valueText={fill(c.used, { used: formatNumber(data.consumed), total: formatNumber(data.total) })} />
							<SessionTiles slots={data.slots} today={today} onPick={open} />
						</div>
					</SectionCard>
				</div>

				<div className="flex flex-col gap-6">
					<SectionCard title={c.info}>
						<KeyValueList
							items={[
								{ label: c.days, value: data.schedule },
								{ label: c.start, value: data.start, numeric: true },
								{ label: c.allowance, value: data.allowed_absence > 0 ? fill(c.allowanceOf, { used: formatNumber(data.absent_allowed), max: formatNumber(data.allowed_absence) }) : fill(c.allowanceFree, { used: formatNumber(data.absent_allowed) }) },
								{ label: c.unauthorized, value: formatNumber(data.absent_unauthorized), numeric: true },
							]}
						/>
					</SectionCard>
					<SectionCard title={t.manage.courseStatus}>
						<CourseActions course={data} />
					</SectionCard>
					<SectionCard title={c.payments}>
						{data.payments && data.payments.length > 0 ? (
							<StaticTable
								caption={c.payments}
								columns={[t.profile.date, t.profile.amount]}
								rows={data.payments.map((payment) => ({ id: String(payment.id), cells: [`${payment.date} · ${KIND[payment.kind] ?? payment.kind}`, formatToman(payment.amount)] }))}
							/>
						) : (
							<EmptyState title={t.profile.noPayments} />
						)}
					</SectionCard>
				</div>
			</div>
			<OutcomeSheet target={target} onClose={() => setTarget(null)} />
		</div>
	);
}

function StudentView({ data, backHref }: { data: CourseDetail; backHref: string }) {
	const today = isoDay(0);
	const next = data.slots.find((slot) => slot.status === null && slot.iso >= today);
	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={data.class_title} backHref={backHref} meta={<StatusChip size="sm" tone={data.status === "ACTIVE" ? "success" : data.status === "PAUSED" ? "warning" : "neutral"} label={data.status_label} />} />
			<div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
				<StatCard label={c.remainingLabel} value={formatNumber(data.remaining)} hint={fill(c.used, { used: formatNumber(data.consumed), total: formatNumber(data.total) })} />
				<StatCard className="col-span-2 xl:col-span-1" label={c.nextSession} value={next ? `${next.weekday} ${next.date}` : "—"} hint={data.schedule} />
				<StatCard label={c.allowance} value={data.allowed_absence > 0 ? fill(c.allowanceOf, { used: formatNumber(data.absent_allowed), max: formatNumber(data.allowed_absence) }) : formatNumber(data.absent_allowed)} />
				<StatCard label={c.unauthorized} value={formatNumber(data.absent_unauthorized)} />
			</div>
			<SectionCard title={c.grid}>
				<div className="flex flex-col gap-4">
					<UsageBar warningAt={101} dangerAt={101} label={c.sessions} used={data.consumed} total={data.total} valueText={fill(c.used, { used: formatNumber(data.consumed), total: formatNumber(data.total) })} />
					<SessionTiles slots={data.slots} today={today} />
				</div>
			</SectionCard>
		</div>
	);
}
