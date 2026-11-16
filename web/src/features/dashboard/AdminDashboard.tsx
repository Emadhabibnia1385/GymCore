import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { EmptyState, ErrorState, PageHeader, PageSkeleton, SectionCard, StatCard, TrendChip, UsageBar } from "@nyxon/nasim";
import { reportQuery } from "@/features/reports/api";
import { formatNumber, formatToman } from "@/shared/format";
import { fill, t } from "@/strings";
import { dashboardQuery } from "./api";
import { TodayCard } from "./TodayCard";
import { YearChart } from "./YearChart";

const d = t.dashboard;

/** The change against last month as a fraction; absent when there is no month to compare. */
const change = (now: number | null, before: number | null) => (now === null || before === null || before === 0 ? null : (now - before) / before);

function Row({ to, params, title, detail, aside, danger }: { to: string; params?: Record<string, string>; title: string; detail?: string; aside: string; danger?: boolean }) {
	return (
		<li>
			<Link to={to} params={params} className="flex items-center justify-between gap-3 rounded-field border border-border p-3 outline-none hover:bg-surface-secondary focus-visible:ring-2 focus-visible:ring-accent">
				<span className="flex min-w-0 flex-col">
					<span className="truncate font-medium">{title}</span>
					{detail ? <span className="truncate text-xs text-muted">{detail}</span> : null}
				</span>
				<span className={danger ? "shrink-0 font-medium text-danger tabular-nums" : "shrink-0 text-sm text-muted tabular-nums"}>{aside}</span>
			</Link>
		</li>
	);
}

export function AdminDashboard() {
	const { data, isPending, isError, refetch } = useQuery(dashboardQuery);
	// The report adds what the dashboard alone doesn't know: last month, attendance, ending courses.
	const report = useQuery(reportQuery(null)).data;
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;

	const k = report?.kpis;
	const incomeChange = k ? change(k.income_this_month, k.income_last_month) : null;
	const expenseChange = k ? change(k.expenses_this_month, k.expenses_last_month) : null;
	const attendance = report?.attendance;
	const counted = attendance ? attendance.present + attendance.absent_allowed + attendance.absent_unauthorized : 0;
	const todo = [
		{ to: "/followups", label: d.dueToday, count: data.follow_ups.due },
		{ to: "/followups", label: d.renewals, count: data.follow_ups.renewals },
		{ to: "/followups", label: d.openLeads, count: data.follow_ups.open_leads },
		{ to: "/reports", label: d.ending, count: k?.ending_soon ?? 0 },
	];

	return (
		<div className="flex flex-col gap-6">
			<PageHeader
				title={d.title}
				description={data.today_label}
				actions={
					<div className="flex flex-wrap gap-2">
						<Link to="/attendance" className="rounded-field bg-accent px-3 py-1.5 text-sm font-medium text-accent-foreground">{t.nav.attendance}</Link>
						<Link to="/students" className="rounded-field border border-border px-3 py-1.5 text-sm hover:bg-surface-secondary">{t.nav.students}</Link>
						<Link to="/finance" className="rounded-field border border-border px-3 py-1.5 text-sm hover:bg-surface-secondary">{t.nav.finance}</Link>
					</div>
				}
			/>

			<div className="grid grid-cols-1 gap-3 min-[480px]:grid-cols-2 xl:grid-cols-4">
				<StatCard label={d.income} value={formatToman(data.month.income)} hint={`${data.month.label} · ${fill(d.paymentsHint, { n: formatNumber(data.month.payments) })}`} trend={incomeChange === null ? undefined : <TrendChip change={incomeChange} suffix={d.vsLast} />} />
				<StatCard label={d.expenses} value={formatToman(data.month.expenses)} hint={data.month.label} trend={expenseChange === null ? undefined : <TrendChip change={expenseChange} isInverse suffix={d.vsLast} />} />
				<StatCard label={d.net} value={formatToman(data.month.net)} hint={data.month.label} />
				<StatCard label={d.owingTitle} value={formatToman(data.owing.total)} hint={data.owing.count ? fill(t.reports.kpi.owingHint, { n: formatNumber(data.owing.count) }) : d.owingNone} />
			</div>

			<div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-3">
				<div className="min-w-0 xl:col-span-2">
					<TodayCard />
				</div>
				<div className="flex flex-col gap-6">
					<SectionCard title={d.attention}>
						{todo.every((row) => row.count === 0) ? (
							<EmptyState title={d.attentionNone} />
						) : (
							<ul className="flex flex-col gap-2">
								{todo.filter((row) => row.count > 0).map((row) => (
									<Row key={row.label} to={row.to} title={row.label} aside={formatNumber(row.count)} />
								))}
							</ul>
						)}
					</SectionCard>
					<SectionCard title={d.attendance}>
						{counted === 0 ? (
							<EmptyState title={t.reports.attendance.none} />
						) : (
							<UsageBar warningAt={101} dangerAt={101} label={fill(d.attendanceHint, { p: formatNumber(attendance!.present), t: formatNumber(counted) })} used={attendance!.present} total={counted} valueText={`${formatNumber(attendance!.rate)}٪`} />
						)}
					</SectionCard>
					<div className="grid grid-cols-2 gap-3">
						<StatCard label={d.students} value={formatNumber(data.totals.clients)} />
						<StatCard label={d.activeCourses} value={formatNumber(data.totals.active_courses)} />
					</div>
				</div>
			</div>

			<div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-3">
				<div className="min-w-0 xl:col-span-2">
					<YearChart year={data.year_label} months={data.months} />
				</div>
				<div className="flex flex-col gap-6">
					<SectionCard title={d.owingTitle} description={data.owing.count ? fill(d.owingHint, { count: formatNumber(data.owing.count), total: formatToman(data.owing.total) }) : undefined} actions={<Link to="/finance" className="text-sm text-accent underline">{d.openOwing}</Link>}>
						{!report || report.debtors.length === 0 ? (
							<EmptyState title={d.owingNone} />
						) : (
							<ul className="flex flex-col gap-2">
								{report.debtors.slice(0, 5).map((row) => (
									<Row key={row.course_id} to="/courses/$id" params={{ id: String(row.course_id) }} title={row.student} detail={row.class_title} aside={formatToman(row.amount)} danger />
								))}
							</ul>
						)}
					</SectionCard>
					{report && report.ending_soon.length > 0 ? (
						<SectionCard title={d.ending} actions={<Link to="/reports" className="text-sm text-accent underline">{d.more}</Link>}>
							<ul className="flex flex-col gap-2">
								{report.ending_soon.slice(0, 4).map((row) => (
									<Row key={row.course_id} to="/courses/$id" params={{ id: String(row.course_id) }} title={row.student} detail={row.class_title} aside={fill(d.endingLeft, { n: formatNumber(row.remaining) })} />
								))}
							</ul>
						</SectionCard>
					) : null}
				</div>
			</div>
		</div>
	);
}
