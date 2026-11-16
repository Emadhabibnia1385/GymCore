import { StatusChip, type StatusTone } from "@nyxon/nasim";
import { fill, t } from "@/strings";
import { formatNumber } from "@/shared/format";
import type { Slot } from "./api";

const TONES: Record<string, StatusTone> = { PRESENT: "success", ABSENT_UNAUTHORIZED: "danger", ABSENT_ALLOWED: "info", COACH_CANCELLED: "info", HOLIDAY: "neutral", MOVED: "info" };
// A session's tile, tinted by its outcome so the whole course reads at a glance.
const TILE: Record<string, string> = {
	PRESENT: "border-success/50 bg-success/10",
	ABSENT_UNAUTHORIZED: "border-danger/50 bg-danger/10",
	ABSENT_ALLOWED: "border-warning/50 bg-warning/10",
	COACH_CANCELLED: "border-info/50 bg-info/10",
	HOLIDAY: "border-border bg-surface-secondary",
	MOVED: "border-info/50 bg-info/10",
};

/** A course's sessions as tiles: the coach taps one to record it, a student just reads them. */
export function SessionTiles({ slots, today, onPick }: { slots: Slot[]; today: string; onPick?: (slot: Slot) => void }) {
	return (
		<ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">
			{slots.map((slot) => {
				const body = (
					<>
						<span className="flex items-center justify-between gap-1">
							<span className="text-xs text-muted">{slot.weekday}</span>
							{slot.session_no ? <span className="text-xs font-bold tabular-nums text-accent">{`#${formatNumber(slot.session_no)}`}</span> : null}
						</span>
						<span className="font-semibold tabular-nums">{slot.date}</span>
						<StatusChip size="sm" tone={slot.status ? (TONES[slot.status] ?? "neutral") : "neutral"} label={slot.label} />
					</>
				);
				const look = `flex w-full flex-col gap-1 rounded-field border p-2.5 text-start ${slot.status ? (TILE[slot.status] ?? "border-border") : "border-dashed border-border"} ${slot.iso === today ? "ring-2 ring-accent" : ""}`;
				return (
					<li key={slot.iso}>
						{onPick ? (
							<button type="button" onClick={() => onPick(slot)} className={`${look} outline-none transition-colors hover:brightness-125 focus-visible:ring-2 focus-visible:ring-accent`}>
								{body}
							</button>
						) : (
							<div className={look} aria-label={fill(t.course.sessionAria, { weekday: slot.weekday, date: slot.date, status: slot.label })}>
								{body}
							</div>
						)}
					</li>
				);
			})}
		</ul>
	);
}
