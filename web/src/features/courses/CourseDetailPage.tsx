import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { EmptyState, ErrorState, KeyValueList, PageHeader, PageSkeleton, SectionCard, StatCard, StaticTable, StatusChip, type StatusTone, UsageBar } from "@nyxon/nasim";
import { useState } from "react";
import { OutcomeSheet, type Target } from "@/features/attendance";
import { CourseActions } from "@/features/manage";
import { isoDay } from "@/shared/DatePick";
import { formatNumber, formatToman } from "@/shared/format";
import { fill, t } from "@/strings";
import { courseQuery, type CourseDetail, type Slot } from "./api";
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
// A session's tile, tinted by its outcome so the whole course reads at a glance.
const TILE: Record<string, string> = {
	PRESENT: "border-success/50 bg-success/10",
	ABSENT_UNAUTHORIZED: "border-danger/50 bg-danger/10",
	ABSENT_ALLOWED: "border-warning/50 bg-warning/10",
	COACH_CANCELLED: "border-info/50 bg-info/10",
	HOLIDAY: "border-border bg-surface-secondary",
	MOVED: "border-info/50 bg-info/10",
};
const KIND: Record<string, string> = { TUITION: "شهریه", GYM_FEE: "ورودی باشگاه", OTHER: "سایر" };

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
							<ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">
								{data.slots.map((slot) => (
									<li key={slot.iso}>
										<button
											type="button"
											onClick={() => open(slot)}
											className={`flex w-full flex-col gap-1 rounded-field border p-2.5 text-start outline-none transition-colors hover:brightness-125 focus-visible:ring-2 focus-visible:ring-accent ${slot.status ? (TILE[slot.status] ?? "border-border") : "border-dashed border-border"} ${slot.iso === today ? "ring-2 ring-accent" : ""}`}
										>
											<span className="flex items-center justify-between gap-1">
												<span className="text-xs text-muted">{slot.weekday}</span>
												{slot.session_no ? <span className="text-xs font-bold tabular-nums text-accent">{`#${formatNumber(slot.session_no)}`}</span> : null}
											</span>
											<span className="font-semibold tabular-nums">{slot.date}</span>
											<Outcome slot={{ ...slot, session_no: null }} />
										</button>
									</li>
								))}
							</ul>
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
	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={data.class_title} backHref={backHref} />
			<CourseSummaryCard course={data} />
			<SectionCard title={c.grid}>
				<StaticTable caption={c.gridCaption} columns={[c.date, c.outcome]} rows={data.slots.map((slot, index) => ({ id: String(index), cells: [`${slot.weekday} ${slot.date}`, <Outcome key="o" slot={slot} />] }))} />
			</SectionCard>
		</div>
	);
}

