import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { BarTable, Button, EmptyState, ErrorState, PageHeader, PageSkeleton, SectionCard, StatCard, StaticTable, StatusChip } from "@nyxon/nasim";
import { useState } from "react";
import { YearChart } from "@/features/dashboard/YearChart";
import { formatNumber, formatToman } from "@/shared/format";
import { fill, t } from "@/strings";
import { expensesQuery, monthQuery, owingQuery, yearQuery } from "./api";
import { ExpenseSheet } from "./ExpenseSheet";
import { PaymentSheet, type PaymentTarget } from "./PaymentSheet";

const m = t.money;

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

	return (
		<div className="flex flex-col gap-6">
			<PageHeader
				title={m.title}
				actions={
					<Button size="sm" onPress={() => setExpenseOpen(true)}>
						{m.recordExpense}
					</Button>
				}
			/>

			<SectionCard title={`${m.month} — ${data.label}`}>
				<div className="flex flex-col gap-4">
					<div className="flex items-center justify-between gap-2">
						<Button size="sm" variant="secondary" onPress={() => setMonth(data.prev)}>{m.prevMonth}</Button>
						{data.next ? <Button size="sm" variant="secondary" onPress={() => setMonth(data.next)}>{m.nextMonth}</Button> : null}
					</div>
					<div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
						<StatCard label={m.income} value={formatToman(data.income)} hint={`${fill(m.payments, { n: formatNumber(data.payments) })}${data.corrections ? ` ${fill(m.corrections, { n: formatNumber(data.corrections) })}` : ""}`} />
						<StatCard label={m.expenses} value={formatToman(data.expenses)} />
						<StatCard label={m.net} value={formatToman(data.net)} />
					</div>
					<div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
						<BarTable title={m.incomeByKind} labelHeader={m.kind} valueHeaders={[m.amount]} empty={m.none} rows={data.income_by_kind.map((line) => ({ key: line.key, label: line.label, value: Math.max(line.amount, 0), cells: [formatToman(line.amount)] }))} />
						<BarTable title={m.expensesByCategory} labelHeader={m.category} valueHeaders={[m.amount]} empty={m.none} rows={data.expenses_by_category.map((line) => ({ key: line.key, label: line.label, value: Math.max(line.amount, 0), cells: [formatToman(line.amount)] }))} />
					</div>
				</div>
			</SectionCard>

			<SectionCard title={m.owing} description={m.owingHint}>
				{owing.data && owing.data.length > 0 ? (
					<ul className="flex flex-col gap-2">
						{owing.data.map((row) => (
							<li key={row.course_id}>
								<button
									type="button"
									className="flex min-h-14 w-full items-center justify-between gap-3 rounded-field border border-border bg-surface p-4 text-start outline-none hover:bg-surface-secondary focus-visible:ring-2 focus-visible:ring-accent"
									onClick={() => setPayment({ personId: row.person_id, courseId: row.course_id, name: row.student, course: row.class_title })}
								>
									<span className="flex flex-col">
										<span className="font-medium">{row.student}</span>
										<span className="text-xs text-muted">{row.class_title}</span>
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

			{year.data ? (
				<>
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
				</>
			) : null}

			<PaymentSheet target={payment} onClose={() => setPayment(null)} />
			<ExpenseSheet isOpen={expenseOpen} onClose={() => setExpenseOpen(false)} />
		</div>
	);
}
