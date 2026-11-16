import { queryOptions, useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { EmptyState, ErrorState, Notice, PageHeader, PageSkeleton, SectionCard, StatCard, StatusChip, type StatusTone, UsageBar } from "@nyxon/nasim";
import type { CourseSummary } from "@/features/courses";
import { apiFetch } from "@/shared/api";
import { formatNumber } from "@/shared/format";
import { PersonAvatar } from "@/shared/PersonAvatar";
import { fill, t } from "@/strings";

type Program = { id: number; title: string; type_title: string; date: string };
type Home = {
	name: string;
	avatar: number | null;
	active_course: CourseSummary | null;
	programs: number;
	packages: number;
	rate: number | null;
	renew: boolean;
	upcoming: { iso: string; date: string; weekday: string; time: string }[];
	recent: { iso: string; date: string; weekday: string; status: string; label: string; session_no: number | null }[];
	latest_programs: Program[];
};
const homeQuery = queryOptions({ queryKey: ["me", "home"], queryFn: () => apiFetch<Home>("/api/me/home") });
const s = t.student;
const TONES: Record<string, StatusTone> = { PRESENT: "success", ABSENT_UNAUTHORIZED: "danger", ABSENT_ALLOWED: "info", COACH_CANCELLED: "info", HOLIDAY: "neutral", MOVED: "info" };
const linkButton = "inline-flex min-h-10 items-center rounded-field px-4 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-accent";

export function StudentHome() {
	const { data, isPending, isError, refetch } = useQuery(homeQuery);
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;
	const course = data.active_course;
	const next = data.upcoming[0];

	return (
		<div className="flex flex-col gap-6">
			<PageHeader
				title={fill(s.hello, { name: data.name })}
				description={course ? course.class_title : s.subscription}
				meta={<PersonAvatar id={0} name={data.name} size={44} src={data.avatar ? `/api/me/avatar?v=${data.avatar}` : null} />}
			/>

			{data.renew ? (
				<Notice tone={course ? "warning" : "info"} title={course ? s.renewTitle : s.noSubscription}>
					<span className="flex flex-wrap items-center gap-3">
						<span>{course ? fill(s.renewBody, { n: formatNumber(course.remaining) }) : s.noSubscriptionHint}</span>
						<Link to="/request" className={`${linkButton} bg-accent text-accent-foreground`}>{t.course.requestAction}</Link>
					</span>
				</Notice>
			) : null}

			{course ? (
				<div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
					<StatCard label={t.course.remainingLabel} value={formatNumber(course.remaining)} hint={fill(t.course.used, { used: formatNumber(course.consumed), total: formatNumber(course.total) })} />
					<StatCard className="col-span-2 xl:col-span-1" label={s.next} value={next ? `${next.weekday} ${next.date}` : "—"} hint={next?.time || course.schedule} />
					<StatCard label={s.rate} value={data.rate === null ? "—" : `${formatNumber(data.rate)}٪`} hint={s.rateHint} />
					<StatCard label={t.course.allowance} value={course.allowed_absence > 0 ? fill(t.course.allowanceOf, { used: formatNumber(course.absent_allowed), max: formatNumber(course.allowed_absence) }) : formatNumber(course.absent_allowed)} />
				</div>
			) : null}

			{course ? (
				<SectionCard
					title={s.progress}
					actions={<Link to="/courses/$id" params={{ id: String(course.id) }} className="text-sm text-accent underline">{s.openCourse}</Link>}
				>
					<UsageBar warningAt={101} dangerAt={101} label={t.course.sessions} used={course.consumed} total={course.total} valueText={fill(t.course.used, { used: formatNumber(course.consumed), total: formatNumber(course.total) })} />
				</SectionCard>
			) : (
				<EmptyState title={s.noSubscription} description={s.noSubscriptionHint} action={{ label: t.course.requestAction, href: "/request" }} />
			)}

			<div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-3">
				<div className="flex min-w-0 flex-col gap-6 lg:col-span-2">
					{course ? (
						<>
							<SectionCard title={s.upcoming}>
								{data.upcoming.length === 0 ? (
									<EmptyState title={s.noUpcoming} />
								) : (
									<ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
										{data.upcoming.map((slot, index) => (
											<li key={slot.iso} className={`flex items-center justify-between gap-3 rounded-field border p-3 ${index === 0 ? "border-accent bg-accent/10" : "border-border"}`}>
												<span className="flex flex-col">
													<span className="font-medium">{slot.weekday}</span>
													<span className="text-xs text-muted tabular-nums">{slot.date}</span>
												</span>
												<span className="text-sm tabular-nums text-muted">{slot.time || "—"}</span>
											</li>
										))}
									</ul>
								)}
							</SectionCard>
							<SectionCard title={s.recent}>
								{data.recent.length === 0 ? (
									<EmptyState title={s.noRecent} />
								) : (
									<ul className="flex flex-col gap-2">
										{data.recent.map((slot) => (
											<li key={slot.iso} className="flex items-center justify-between gap-3 rounded-field border border-border p-3">
												<span className="flex flex-col">
													<span className="font-medium">{slot.weekday}</span>
													<span className="text-xs text-muted tabular-nums">{slot.date}</span>
												</span>
												<StatusChip size="sm" tone={TONES[slot.status] ?? "neutral"} label={slot.session_no ? `${slot.label} · ${fill(t.course.sessionNo, { n: slot.session_no })}` : slot.label} />
											</li>
										))}
									</ul>
								)}
							</SectionCard>
						</>
					) : null}
				</div>

				<SectionCard title={s.library} description={s.libraryHint} actions={<Link to="/programs" className="text-sm text-accent underline">{s.all}</Link>}>
					<div className="flex flex-col gap-3">
						<p className="text-sm text-muted">{fill(s.counts, { programs: formatNumber(data.programs), packages: formatNumber(data.packages) })}</p>
						{data.latest_programs.length === 0 ? (
							<EmptyState title={s.noPrograms} />
						) : (
							<ul className="flex flex-col gap-2">
								{data.latest_programs.map((program) => (
									<li key={program.id} className="flex items-center justify-between gap-3 rounded-field border border-border p-3">
										<span className="flex min-w-0 flex-col">
											<span className="truncate font-medium">{program.title}</span>
											<span className="truncate text-xs text-muted">{program.type_title}</span>
										</span>
										<span className="shrink-0 text-xs text-muted tabular-nums">{program.date}</span>
									</li>
								))}
							</ul>
						)}
					</div>
				</SectionCard>
			</div>
		</div>
	);
}
