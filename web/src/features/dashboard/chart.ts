import { formatNumber } from "@/shared/format";

const compact = new Intl.NumberFormat("fa-IR", { notation: "compact", maximumFractionDigits: 1 });

/** Three even gridlines from zero to just above the largest value, rounded to 1/2/5 × 10ⁿ. */
export function yTicks(max: number): { value: number; label: string }[] {
	const rough = Math.max(max, 1) / 3;
	const magnitude = 10 ** Math.floor(Math.log10(rough));
	const step = [1, 2, 5, 10].map((m) => m * magnitude).find((s) => s >= rough) ?? rough;
	return [0, 1, 2, 3].map((i) => ({ value: i * step, label: i === 0 ? formatNumber(0) : compact.format(i * step) }));
}
