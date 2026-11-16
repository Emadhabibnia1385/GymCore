import { AreaChart } from "@nyxon/nasim";
import { formatToman } from "@/shared/format";
import { fill, t } from "@/strings";
import { yTicks } from "./chart";

const d = t.dashboard;
export type MonthPoint = { month: number; label: string; income: number; expenses: number };

/** Income and expenses for each month of a Jalali year. */
export function YearChart({ year, months }: { year: string; months: MonthPoint[] }) {
	const peak = months.reduce((best, row) => (row.income > best.income ? row : best), months[0]);
	const ceiling = Math.max(0, ...months.flatMap((row) => [row.income, row.expenses]));
	const figure = (value: number) => ({ value, text: formatToman(value) });
	return (
		<AreaChart
			data-testid="year-chart"
			title={fill(d.chartTitle, { year })}
			summary={fill(d.chartSummary, { year, peak: peak.label })}
			empty={d.chartEmpty}
			ticks={months.map((row) => ({ key: String(row.month), label: row.label, title: `${row.label} ${year}` }))}
			series={[
				{ key: "income", label: d.chartIncome, points: months.map((row) => figure(row.income)) },
				{ key: "expenses", label: d.chartExpenses, points: months.map((row) => figure(row.expenses)) },
			]}
			yTicks={yTicks(ceiling)}
			table={{ showLabel: d.chartShowTable, label: d.chartTableLabel, stepHeader: d.chartStep }}
		/>
	);
}
