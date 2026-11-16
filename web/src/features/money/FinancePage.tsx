import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AreaChart, BarTable, Button, EmptyState, ErrorState, PageHeader, PageSkeleton, SectionCard, StatCard, StaticTable, StatusChip, TrendChip } from "@nyxon/nasim";
import { useState } from "react";
import { yTicks } from "@/features/dashboard/chart";
import { formatNumber, formatToman } from "@/shared/format";
import { TINT, tintStyle } from "@/shared/personColor";
import { fill, t } from "@/strings";
import { owingQuery, periodQuery, yearQuery, type Line, type Period, type PeriodQuery } from "./api";
import { ExpenseSheet } from "./ExpenseSheet";
import { PaymentSheet, type PaymentTarget } from "./PaymentSheet";
import { type Mode, PeriodBar } from "./PeriodBar";

const m = t.money;
const change = (now: number, before: number | undefined) => (before ? (now - before) / before : null);
const lines = (rows: Line[]) => rows.map((line) => ({ key: line.key, label: line.label, value: Math.max(line.amount, 0), cells: [formatToman(line.amount)] }));

export function FinancePage() {
	const [mode, setMode] = useState<Mode>("month");
	const [query, setQuery] = useState<PeriodQuery>({});
	const [payment, setPayment] = useState<PaymentTarget | null>(null);
	const [expenseOpen, setExpenseOpen] = useState(false);
	const report = useQuery({ ...periodQuery(query), placeholderData: keepPreviousData });
	const jy = report.data?.jy ?? 0;
	const year = useQuery({ ...yearQuery(jy), enabled: jy > 0 });
	const owing = useQuery(owingQuery);

	if (report.isPending) return <PageSkeleton />;
	if (report.isError) return <ErrorState as="h1" onRetry={() => void report.refetch()} />;
	const data = report.data;
	const incomeChange = change(data.income, data.previous.income);
	const expenseChange = change(data.expenses, data.previous.expenses);
	const vs = data.kind === "year" ? t.money.vsLastYear : data.kind === "month" ? t.dashboard.vsLast : t.money.vsBefore;
	const owed = (owing.data ?? []).reduce((sum, row) => sum + row.amount, 0);
	const kept = data.income > 0 ? Math.round((data.net / data.income) * 100) : null;

	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={m.title} description={data.label} actions={<Button size="sm" onPress={() => setExpenseOpen(true)}>{m.recordExpense}</Button>} />

			<PeriodBar mode={mode} onMode={setMode} data={data} query={query} onQuery={setQuery} />

			<div className="grid grid-cols-1 gap-3 min-[480px]:grid-cols-2 xl:grid-cols-4">
				<StatCard label={m.income} value={formatToman(data.income)} hint={`${fill(m.payments, { n: formatNumber(data.payments) })}${data.corrections ? ` ${fill(m.corrections, { n: formatNumber(data.corrections) })}` : ""}`} trend={incomeChange === null ? undefined : <TrendChip change={incomeChange} suffix={vs} />} />
				<StatCard label={m.expenses} value={formatToman(data.expenses)} hint={fill(m.expenseCount, { n: formatNumber(data.expense_rows.length) })} trend={expenseChange === null ? undefined : <TrendChip change={expenseChange} isInverse suffix={vs} />} />
				<StatCard label={m.net} value={formatToman(data.net)} hint={kept === null || kept < 0 ? undefined : fill(m.kept, { p: formatNumber(kept) })} />
				<StatCard label={m.owing} value={formatToman(owed)} hint={fill(t.reports.kpi.owingHint, { n: formatNumber(owing.data?.length ?? 0) })} />
			</div>

			<div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-2">
				<SectionCard title={m.owing} description={m.owingHint}>
					{owing.data && owing.data.length > 0 ? (
						<ul className="flex flex-col gap-2">
							{owing.data.map((row) => (
								<li key={row.course_id}>
									<button
										type="button"
										style={tintStyle(row.person_id)}
										className="flex min-h-14 w-full items-center justify-between gap-3 rounded-field border border-border bg-surface p-3 text-start outline-none hover:bg-surface-secondary focus-visible:ring-2 focus-visible:ring-accent"
										onClick={() => setPayment({ personId: row.person_id, courseId: row.course_id, name: row.student, course: row.class_title })}
									>
										<span className="flex min-w-0 items-center gap-3">
											<span aria-hidden className={`flex size-9 shrink-0 items-center justify-center rounded-full text-sm font-bold ${TINT}`}>{row.student.trim().charAt(0)}</span>
											<span className="flex min-w-0 flex-col">
												<span className="truncate font-medium">{row.student}</span>
												<span className="truncate text-xs text-muted">{row.class_title}</span>
											</span>
										</span>
										<StatusChip size="sm" tone="danger" label={formatToman(row.amount)} />
									</button>
								</li>
							))}
						</ul>
					) : (
						<EmptyState title={m.owingNone} />
					)}
				</SectionCard>

				<SectionCard title={m.expensesOfPeriod}>
					{data.expense_rows.length > 0 ? (
						<StaticTable
							caption={m.expensesOfPeriod}
							columns={[m.date, m.category, m.amount]}
							rows={data.expense_rows.map((row) => ({
								id: String(row.id),
								cells: [row.date, `${row.category_label}${row.note ? ` · ${row.note}` : ""}`, row.amount < 0 ? <StatusChip key="c" size="sm" tone="warning" label={`${m.correctionMark} ${formatToman(row.amount)}`} /> : formatToman(row.amount)],
							}))}
						/>
					) : (
						<EmptyState title={m.expensesNone} />
					)}
				</SectionCard>

				<SectionCard title={m.incomeByKind}>
					<BarTable title={m.incomeByKind} hideTitle labelHeader={m.kind} valueHeaders={[m.amount]} empty={m.none} rows={lines(data.income_by_kind)} />
				</SectionCard>
				<SectionCard title={m.expensesByCategory}>
					<BarTable title={m.expensesByCategory} hideTitle labelHeader={m.category} valueHeaders={[m.amount]} empty={m.none} tone="info" rows={lines(data.expenses_by_category)} />
				</SectionCard>
			</div>

			{year.data ? (
				<div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-2">
					<SectionCard title={fill(m.chartOf, { label: data.label })}>
						<PeriodChart data={data} />
					</SectionCard>
					<SectionCard title={fill(m.year, { year: String(year.data.jy) })}>
						<StaticTable
							caption={m.yearCaption}
							columns={[m.monthCol, m.income, m.expenses, m.net]}
							rows={[
								...year.data.rows.map((row) => ({ id: String(row.jm), cells: [row.label, formatToman(row.income), formatToman(row.expenses), formatToman(row.net)] })),
								{ id: "total", cells: [m.yearTotal, formatToman(year.data.income), formatToman(year.data.expenses), formatToman(year.data.net)] },
							]}
							className="min-w-[30rem]"
						/>
					</SectionCard>
				</div>
			) : null}

			<PaymentSheet target={payment} onClose={() => setPayment(null)} />
			<ExpenseSheet isOpen={expenseOpen} onClose={() => setExpenseOpen(false)} />
		</div>
	);
}

function PeriodChart({ data }: { data: Period }) {
	const peak = data.series.reduce((best, row) => (row.income > best.income ? row : best), data.series[0]);
	const ceiling = Math.max(0, ...data.series.flatMap((row) => [row.income, row.expenses]));
	const figure = (value: number) => ({ value, text: formatToman(value) });
	return (
		<AreaChart
			title={fill(m.chartOf, { label: data.label })}
			summary={fill(m.chartSummary, { peak: peak?.label ?? "—" })}
			empty={t.dashboard.chartEmpty}
			ticks={data.series.map((row) => ({ key: row.key, label: row.label, title: row.label }))}
			series={[
				{ key: "income", label: t.dashboard.chartIncome, points: data.series.map((row) => figure(row.income)) },
				{ key: "expenses", label: t.dashboard.chartExpenses, points: data.series.map((row) => figure(row.expenses)) },
			]}
			yTicks={yTicks(ceiling)}
			table={{ showLabel: t.dashboard.chartShowTable, label: t.dashboard.chartTableLabel, stepHeader: m.step }}
		/>
	);
}
