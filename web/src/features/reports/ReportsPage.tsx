import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { AreaChart, BarTable, Button, ColumnChart, EmptyState, ErrorState, PageHeader, PageSkeleton, SectionCard, StatCard, TrendChip, UsageBar } from "@nyxon/nasim";
import { useState } from "react";
import { yTicks } from "@/features/dashboard/chart";
import { formatNumber, formatToman } from "@/shared/format";
import { fill, t } from "@/strings";
import { reportQuery, type Line, type Report } from "./api";

const r = t.reports;

/** The change from last month, as a fraction (0.12 is +12%); absent when there is nothing to compare. */
function change(now: number | null, before: number | null): number | null {
	if (now === null || before === null || before === 0) return null;
	return (now - before) / before;
}

const lines = (rows: Line[]) => rows.map((row) => ({ key: row.key, label: row.label, value: Math.max(row.amount, 0), cells: [formatToman(row.amount)] }));

function PersonRows({ rows }: { rows: { course_id: number; student: string; class_title: string; aside: string; danger?: boolean }[] }) {
	return (
		<ul className="flex flex-col gap-2">
			{rows.map((row) => (
				<li key={row.course_id}>
					<Link to="/courses/$id" params={{ id: String(row.course_id) }} className="flex items-center justify-between gap-3 rounded-field border border-border p-3 hover:bg-surface-secondary">
						<span className="flex flex-col">
							<span className="font-medium">{row.student}</span>
							<span className="text-xs text-muted">{row.class_title}</span>
						</span>
						<span className={row.danger ? "font-medium text-danger tabular-nums" : "text-sm text-muted"}>{row.aside}</span>
					</Link>
				</li>
			))}
		</ul>
	);
}

export function ReportsPage() {
	const [year, setYear] = useState<number | null>(null);
	const { data, isPending, isError, refetch } = useQuery({ ...reportQuery(year), placeholderData: keepPreviousData });
	if (isPending) return <PageSkeleton />;
	if (isError) return <ErrorState as="h1" onRetry={() => void refetch()} />;
	const k = data.kpis;
	const a = data.attendance;
	const incomeChange = change(k.income_this_month, k.income_last_month);
	const expenseChange = change(k.expenses_this_month, k.expenses_last_month);
	const counted = a.present + a.absent_allowed + a.absent_unauthorized;

	return (
		<div className="flex flex-col gap-6">
			<PageHeader
				title={r.title}
				description={r.hint}
				actions={
					<div className="flex items-center gap-2">
						<Button size="sm" variant="secondary" onPress={() => setYear(data.year - 1)}>{r.prevYear}</Button>
						<span className="min-w-12 text-center font-medium tabular-nums">{String(data.year)}</span>
						<Button size="sm" variant="secondary" onPress={() => setYear(data.year + 1)}>{r.nextYear}</Button>
					</div>
				}
			/>

			<div className="grid grid-cols-1 gap-3 min-[480px]:grid-cols-2 lg:grid-cols-4">
				<StatCard label={r.kpi.income} value={formatToman(k.income_year)} trend={incomeChange === null ? undefined : <TrendChip change={incomeChange} suffix={r.kpi.vsLast} />} />
				<StatCard label={r.kpi.expenses} value={formatToman(k.expenses_year)} trend={expenseChange === null ? undefined : <TrendChip change={expenseChange} isInverse suffix={r.kpi.vsLast} />} />
				<StatCard label={r.kpi.net} value={formatToman(k.net_year)} />
				<StatCard label={r.kpi.owing} value={formatToman(k.owing_total)} hint={fill(r.kpi.owingHint, { n: formatNumber(k.owing_count) })} />
				<StatCard label={r.kpi.students} value={formatNumber(k.students)} />
				<StatCard label={r.kpi.courses} value={formatNumber(k.courses_active)} hint={fill(r.kpi.coursesHint, { done: formatNumber(k.courses_finished), paused: formatNumber(k.courses_paused) })} />
				<StatCard label={r.kpi.ending} value={formatNumber(k.ending_soon)} hint={r.kpi.endingHint} />
				<StatCard label={r.kpi.average} value={formatToman(k.average_payment)} />
			</div>

			<SectionCard title={fill(r.chart.year, { year: String(data.year) })}>
				<YearArea report={data} />
			</SectionCard>

			<div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
				<SectionCard title={r.attendance.title}>
					<div className="flex flex-col gap-4">
						{counted + a.cancelled + a.holiday === 0 ? (
							<EmptyState title={r.attendance.none} />
						) : (
							<>
								<UsageBar warningAt={101} dangerAt={101} label={fill(r.kpi.attendanceHint, { p: formatNumber(a.present), t: formatNumber(counted) })} used={a.present} total={counted || null} valueText={`${formatNumber(a.rate)}٪`} />
								<ul className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-5">
									{(
										[
											[r.attendance.present, a.present],
											[r.attendance.allowed, a.absent_allowed],
											[r.attendance.unauthorized, a.absent_unauthorized],
											[r.attendance.cancelled, a.cancelled],
											[r.attendance.holiday, a.holiday],
										] as const
									).map(([label, count]) => (
										<li key={label} className="flex flex-col rounded-field border border-border p-2">
											<span className="text-muted">{label}</span>
											<span className="text-lg font-semibold tabular-nums">{formatNumber(count)}</span>
										</li>
									))}
								</ul>
							</>
						)}
						<WeeksChart report={data} />
					</div>
				</SectionCard>

				<SectionCard title={r.classes.title}>
					<BarTable
						title={r.classes.title}
						hideTitle
						labelHeader={r.classes.label}
						valueHeaders={[r.classes.income, r.classes.active]}
						empty={r.classes.none}
						rows={data.classes.map((row) => ({ key: row.title, label: row.title, value: Math.max(row.income, 0), cells: [formatToman(row.income), formatNumber(row.active_courses)] }))}
					/>
				</SectionCard>

				<SectionCard title={r.lines.incomeKind}>
					<BarTable title={r.lines.incomeKind} hideTitle labelHeader={r.lines.label} valueHeaders={[r.lines.amount]} empty={r.lines.none} rows={lines(data.income_by_kind)} />
				</SectionCard>
				<SectionCard title={r.lines.expenseCategory}>
					<BarTable title={r.lines.expenseCategory} hideTitle labelHeader={r.lines.label} valueHeaders={[r.lines.amount]} empty={r.lines.none} tone="info" rows={lines(data.expenses_by_category)} />
				</SectionCard>

				<SectionCard title={r.chart.newStudents}>
					<NewStudents report={data} />
				</SectionCard>

				<div className="flex flex-col gap-6">
					<SectionCard title={r.debtors.title}>
						{data.debtors.length === 0 ? <EmptyState title={r.debtors.none} /> : <PersonRows rows={data.debtors.map((row) => ({ ...row, aside: formatToman(row.amount), danger: true }))} />}
					</SectionCard>
					<SectionCard title={r.ending.title}>
						{data.ending_soon.length === 0 ? <EmptyState title={r.ending.none} /> : <PersonRows rows={data.ending_soon.map((row) => ({ ...row, aside: fill(r.ending.left, { n: formatNumber(row.remaining) }) }))} />}
					</SectionCard>
				</div>
			</div>
		</div>
	);
}

function YearArea({ report }: { report: Report }) {
	const peak = report.months.reduce((best, row) => (row.income > best.income ? row : best), report.months[0]);
	const ceiling = Math.max(0, ...report.months.flatMap((row) => [row.income, row.expenses]));
	const figure = (value: number) => ({ value, text: formatToman(value) });
	return (
		<AreaChart
			title={fill(r.chart.year, { year: String(report.year) })}
			summary={fill(r.chart.yearSummary, { peak: peak.label })}
			empty={r.chart.empty}
			ticks={report.months.map((row) => ({ key: String(row.month), label: row.label, title: `${row.label} ${report.year}` }))}
			series={[
				{ key: "income", label: r.chart.income, points: report.months.map((row) => figure(row.income)) },
				{ key: "expenses", label: r.chart.expenses, points: report.months.map((row) => figure(row.expenses)) },
			]}
			yTicks={yTicks(ceiling)}
			table={{ showLabel: r.chart.showTable, label: r.chart.tableLabel, stepHeader: r.chart.step }}
		/>
	);
}

function WeeksChart({ report }: { report: Report }) {
	const peak = report.weeks.reduce((best, row) => (row.present > best.present ? row : best), report.weeks[0]);
	return (
		<ColumnChart
			title={r.chart.weeks}
			summary={fill(r.chart.weeksSummary, { peak: peak.label })}
			empty={r.chart.weeksEmpty}
			tone="success"
			points={report.weeks.map((row) => ({ key: row.label, label: row.label, value: row.present, tooltip: fill(r.chart.weekLine, { label: row.label, p: formatNumber(row.present), a: formatNumber(row.absent) }) }))}
		/>
	);
}

function NewStudents({ report }: { report: Report }) {
	return (
		<ColumnChart
			title={r.chart.newStudents}
			summary={r.chart.newStudentsSummary}
			empty={r.chart.newStudentsEmpty}
			tone="info"
			points={report.months.map((row) => ({ key: String(row.month), label: row.label, value: row.new_students, tooltip: fill(r.chart.newLine, { label: row.label, n: formatNumber(row.new_students), c: formatNumber(row.new_courses) }) }))}
		/>
	);
}
