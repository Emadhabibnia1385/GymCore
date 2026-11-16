import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { BarTable, Button, EmptyState, ErrorState, PageHeader, PageSkeleton, SectionCard, StatCard, StaticTable, StatusChip, TrendChip } from "@nyxon/nasim";
import { useState } from "react";
import { YearChart } from "@/features/dashboard/YearChart";
import { formatNumber, formatToman } from "@/shared/format";
import { TINT, tintStyle } from "@/shared/personColor";
import { fill, t } from "@/strings";
import { expensesQuery, monthQuery, owingQuery, yearQuery, type Line } from "./api";
import { ExpenseSheet } from "./ExpenseSheet";
import { PaymentSheet, type PaymentTarget } from "./PaymentSheet";

const m = t.money;
const change = (now: number, before: number | undefined) => (before ? (now - before) / before : null);
const lines = (rows: Line[]) => rows.map((line) => ({ key: line.key, label: line.label, value: Math.max(line.amount, 0), cells: [formatToman(line.amount)] }));

export function FinancePage() {
	const [month, setMonth] = useState<[number, number] | null>(null);
	const [payment, setPayment] = useState<PaymentTarget | null>(null);
	const [expenseOpen, setExpenseOpen] = useState(false);
	const report = useQuery({ ...monthQuery(month?.[0] ?? null, month?.[1] ?? null), placeholderData: keepPreviousData });
	const jy = report.data?.jy ?? 0;
	const year = useQuery({ ...yearQuery(jy), enabled: jy > 0 });
	const expenses = useQuery({ ...expensesQuery(jy, report.data?.jm ?? 1), enabled: jy > 0 });
	const owing = useQuery(owingQuery);

	if (report.isPending) return <PageSkeleton />;
	if (report.isError) return <ErrorState as="h1" onRetry={() => void report.refetch()} />;
	const data = report.data;
	const before = year.data?.rows.find((row) => row.jm === data.jm - 1);
	const incomeChange = change(data.income, before?.income);
	const expenseChange = change(data.expenses, before?.expenses);
	const owed = (owing.data ?? []).reduce((sum, row) => sum + row.amount, 0);
	const kept = data.income > 0 ? Math.round((data.net / data.income) * 100) : null;

	return (
		<div className="flex flex-col gap-6">
			<PageHeader title={m.title} description={data.label} actions={<Button size="sm" onPress={() => setExpenseOpen(true)}>{m.recordExpense}</Button>} />

			<div className="flex items-center justify-between gap-2 rounded-box border border-border bg-surface p-2">
				<Button size="sm" variant="secondary" onPress={() => setMonth(data.prev)}>{m.prevMonth}</Button>
				<span className="font-semibold">{data.label}</span>
				{data.next ? <Button size="sm" variant="secondary" onPress={() => setMonth(data.next)}>{m.nextMonth}</Button> : <span className="w-20" />}
			</div>

			<div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
				<StatCard label={m.income} value={formatToman(data.income)} hint={`${fill(m.payments, { n: formatNumber(data.payments) })}${data.corrections ? ` ${fill(m.corrections, { n: formatNumber(data.corrections) })}` : ""}`} trend={incomeChange === null ? undefined : <TrendChip change={incomeChange} suffix={t.dashboard.vsLast} />} />
				<StatCard label={m.expenses} value={formatToman(data.expenses)} hint={fill(m.expenseCount, { n: formatNumber(expenses.data?.length ?? 0) })} trend={expenseChange === null ? undefined : <TrendChip change={expenseChange} isInverse suffix={t.dashboard.vsLast} />} />
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

				<SectionCard title={m.expensesOfMonth}>
					{expenses.data && expenses.data.length > 0 ? (
						<StaticTable
							caption={m.expensesOfMonth}
							columns={[m.date, m.category, m.amount]}
							rows={expenses.data.map((row) => ({
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
					<YearChart year={String(year.data.jy)} months={year.data.rows.map((row) => ({ month: row.jm, label: row.label, income: row.income, expenses: row.expenses }))} />
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
