import { useQuery } from "@tanstack/react-query";
import {
	EmptyState,
	ErrorState,
	PageHeader,
	PageSkeleton,
	SectionCard,
	StatCard,
	StaticTable,
} from "@nyxon/nasim";
import { formatNumber, formatToman } from "@/shared/format";
import { fill, t } from "@/strings";
import { dashboardQuery } from "./api";
import { YearChart } from "./YearChart";

const d = t.dashboard;

// A name with what it is for beneath it: one column instead of two keeps a phone from scrolling sideways.
function Person({ name, detail }: { name: string; detail: string }) {
	return (
		<div className="flex flex-col">
			<span>{name}</span>
			<span className="text-xs text-muted">{detail}</span>
		</div>
	);
}

export function AdminDashboard() {
	const { data, isPending, isError, refetch } = useQuery(dashboardQuery);
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;


	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={d.title} description={data.today_label} />

			<div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
				<StatCard label={d.income} value={formatToman(data.month.income)} hint={`${data.month.label} · ${fill(d.paymentsHint, { n: formatNumber(data.month.payments) })}`} />
				<StatCard label={d.expenses} value={formatToman(data.month.expenses)} hint={data.month.label} />
				<StatCard label={d.net} value={formatToman(data.month.net)} hint={data.month.label} />
			</div>

			<div className="grid grid-cols-3 gap-3">
				<StatCard label={d.students} value={formatNumber(data.totals.clients)} />
				<StatCard label={d.activeCourses} value={formatNumber(data.totals.active_courses)} />
				<StatCard label={d.programs} value={formatNumber(data.totals.programs)} />
			</div>

			<YearChart year={data.year_label} months={data.months} />

			<div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
				<SectionCard title={d.owingTitle} description={data.owing.count ? fill(d.owingHint, { count: formatNumber(data.owing.count), total: formatToman(data.owing.total) }) : undefined}>
					{data.owing.top.length === 0 ? (
						<EmptyState title={d.owingNone} />
					) : (
						<StaticTable
							caption={d.owingCaption}
							columns={[d.student, d.amount]}
							rows={data.owing.top.map((row, index) => ({ id: String(index), cells: [<Person key="p" name={row.student} detail={row.class_title} />, formatToman(row.amount)] }))}
						/>
					)}
				</SectionCard>

				<SectionCard title={d.todayTitle}>
					{data.today.length === 0 ? (
						<EmptyState title={d.todayNone} />
					) : (
						<StaticTable
							caption={d.todayCaption}
							columns={[d.time, d.student]}
							rows={data.today.map((row, index) => ({ id: String(index), cells: [row.time || d.noTime, <Person key="p" name={row.student} detail={row.class_title} />] }))}
						/>
					)}
				</SectionCard>
			</div>

			<SectionCard title={d.followUps} description={d.followUpsHint}>
				<div className="grid grid-cols-3 gap-3">
					<StatCard label={d.dueToday} value={formatNumber(data.follow_ups.due)} />
					<StatCard label={d.renewals} value={formatNumber(data.follow_ups.renewals)} />
					<StatCard label={d.openLeads} value={formatNumber(data.follow_ups.open_leads)} />
				</div>
			</SectionCard>
		</div>
	);
}
