import { EmptyState, StatusChip, type StatusTone } from "@nyxon/nasim";
import { formatToman } from "@/shared/format";
import { t } from "@/strings";
import type { ActivityRow } from "./api";

const p = t.profile;
const TONE: Record<string, StatusTone> = { PRESENT: "success", ABSENT_UNAUTHORIZED: "danger", ABSENT_ALLOWED: "warning", COACH_CANCELLED: "info", HOLIDAY: "neutral", MOVED: "info" };
const KIND: Record<ActivityRow["kind"], { label: string; tone: StatusTone }> = {
	attendance: { label: p.kindAttendance, tone: "neutral" },
	payment: { label: p.kindPayment, tone: "success" },
	note: { label: p.kindNote, tone: "neutral" },
	program: { label: p.kindProgram, tone: "info" },
};

/** What happened lately to one student — sessions, payments, notes and programs — newest first. */
export function ActivityList({ rows }: { rows: ActivityRow[] }) {
	if (rows.length === 0) return <EmptyState title={p.noActivity} />;
	return (
		<ol className="flex flex-col">
			{rows.map((row, index) => {
				const tone = row.kind === "attendance" && row.status ? (TONE[row.status] ?? "neutral") : KIND[row.kind].tone;
				return (
					<li key={`${row.kind}-${row.iso}-${index}`} className="flex gap-3 border-s-2 border-border ps-4 pb-4 last:pb-0">
						<div className="-ms-[1.45rem] mt-1 size-2.5 shrink-0 rounded-full bg-accent" aria-hidden />
						<div className="flex min-w-0 flex-1 flex-col gap-1">
							<div className="flex flex-wrap items-center gap-2">
								<StatusChip size="sm" tone={tone} label={row.kind === "attendance" ? row.title : KIND[row.kind].label} />
								<span className="text-xs text-muted tabular-nums">{row.date}</span>
								{row.amount !== null ? <span className={`text-sm font-medium tabular-nums ${row.amount < 0 ? "text-warning" : "text-success"}`}>{formatToman(row.amount)}</span> : null}
							</div>
							{row.kind !== "attendance" ? <span className="text-sm">{row.title}</span> : null}
							{row.detail ? <span className="text-xs text-muted">{row.detail}</span> : null}
						</div>
					</li>
				);
			})}
		</ol>
	);
}
