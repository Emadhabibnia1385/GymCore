import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Notice } from "@nyxon/nasim";
import { t } from "@/strings";
import { recordAttendance, type DayRow } from "./api";

const a = t.attend;

// Every outcome one tap away, in the order the coach reaches for them.
const OPTIONS = [
	{ status: "PRESENT", label: a.opt.present, on: "border-success bg-success/20 text-success" },
	{ status: "ABSENT_ALLOWED", label: a.opt.allowed, on: "border-warning bg-warning/20 text-warning" },
	{ status: "ABSENT_UNAUTHORIZED", label: a.opt.absent, on: "border-danger bg-danger/20 text-danger" },
	{ status: "COACH_CANCELLED", label: a.opt.cancelled, on: "border-info bg-info/20 text-info" },
	{ status: "HOLIDAY", label: a.opt.holiday, on: "border-accent bg-accent/20 text-accent" },
] as const;

/** One session's outcome as a row of buttons — the chosen one lit — plus «more» for a note or a move. */
export function OutcomeButtons({ row, iso, isFuture, onMore }: { row: DayRow; iso: string; isFuture: boolean; onMore: () => void }) {
	const queryClient = useQueryClient();
	const record = useMutation({
		mutationFn: (status: string) => recordAttendance({ course_id: row.course_id, date: iso, status }),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin"] }),
	});
	return (
		<div className="flex flex-col gap-2">
			{record.isError ? <Notice tone="danger" role="alert">{record.error.message}</Notice> : null}
			<div role="group" aria-label={a.pick} className="grid grid-cols-6 gap-1.5">
				{OPTIONS.map((option) => {
					const chosen = row.status === option.status;
					return (
						<button
							key={option.status}
							type="button"
							aria-pressed={chosen}
							disabled={isFuture || record.isPending}
							onClick={() => !chosen && record.mutate(option.status)}
							className={`min-h-11 rounded-field border px-1 text-xs font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50 ${chosen ? option.on : "border-border text-muted hover:bg-surface-secondary"}`}
						>
							{option.label}
						</button>
					);
				})}
				<button
					type="button"
					aria-label={a.more}
					onClick={onMore}
					className="min-h-11 rounded-field border border-border text-lg leading-none text-muted outline-none hover:bg-surface-secondary focus-visible:ring-2 focus-visible:ring-accent"
				>
					⋯
				</button>
			</div>
		</div>
	);
}
