import { Button, DateTimeField } from "@nyxon/nasim";
import { t } from "@/strings";

const c = t.common;

function isoDay(offset: number): string {
	const day = new Date();
	day.setDate(day.getDate() + offset);
	return `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(day.getDate()).padStart(2, "0")}`;
}

/** A date in the Persian calendar (value: ISO `YYYY-MM-DD`), with today/yesterday a tap away. */
export function DatePick({ label, value, onChange, shortcuts = true }: { label: string; value: string; onChange: (iso: string) => void; shortcuts?: boolean }) {
	return (
		<div className="flex flex-col gap-2">
			<DateTimeField
				label={label}
				value={value ? `${value}T00:00` : ""}
				onChange={(next: string) => onChange(next.slice(0, 10))}
				calendarLabel={c.calendar}
				timeLabel={c.time}
				clearLabel={c.clearDate}
			/>
			{shortcuts ? (
				<div className="flex gap-2">
					<Button size="sm" variant="secondary" onPress={() => onChange(isoDay(0))}>{c.today}</Button>
					<Button size="sm" variant="secondary" onPress={() => onChange(isoDay(-1))}>{c.yesterday}</Button>
				</div>
			) : null}
		</div>
	);
}

export { isoDay };
