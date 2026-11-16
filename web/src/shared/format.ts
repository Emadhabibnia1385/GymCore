import { t } from "@/strings";

const digits = new Intl.NumberFormat("fa-IR");

/** Persian digits with thousands separators. */
export function formatNumber(value: number): string {
	return digits.format(value);
}

/** An integer Toman amount, with its unit. */
export function formatToman(amount: number): string {
	return `${formatNumber(amount)} ${t.units.toman}`;
}
