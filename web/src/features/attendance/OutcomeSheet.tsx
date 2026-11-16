import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BottomSheet, Button, Notice, TextField } from "@nyxon/nasim";
import { useState } from "react";
import { DatePick } from "@/shared/DatePick";
import { t } from "@/strings";
import { moveSession, outcomesQuery, recordAttendance } from "./api";

const a = t.attend;

export type Target = { courseId: number; iso: string; title: string; subtitle: string; current: string; isFuture: boolean };

/** One session's outcome: the picker the coach uses from the day view and from a course's grid. */
export function OutcomeSheet({ target, onClose }: { target: Target | null; onClose: () => void }) {
	return (
		<BottomSheet isOpen={target !== null} onOpenChange={(open) => !open && onClose()} title={target?.title ?? ""}>
			{target ? <Body key={`${target.courseId}-${target.iso}`} target={target} onClose={onClose} /> : null}
		</BottomSheet>
	);
}

function Body({ target, onClose }: { target: Target; onClose: () => void }) {
	const queryClient = useQueryClient();
	const outcomes = useQuery(outcomesQuery);
	const [note, setNote] = useState("");
	const [newDate, setNewDate] = useState("");
	const done = async () => {
		await queryClient.invalidateQueries({ queryKey: ["admin"] });
		onClose();
	};
	const record = useMutation({ mutationFn: (status: string) => recordAttendance({ course_id: target.courseId, date: target.iso, status, note: note.trim() || null }), onSuccess: done });
	const move = useMutation({ mutationFn: () => moveSession({ course_id: target.courseId, date: target.iso, new_date: newDate }), onSuccess: done });
	const error = record.error ?? move.error;

	return (
		<div className="flex flex-col gap-5">
			<p className="text-sm text-muted">
				{target.subtitle} · {target.current}
			</p>
			{error ? <Notice tone="danger" role="alert">{error.message}</Notice> : null}
			{target.isFuture ? (
				<Notice tone="info">{a.future}</Notice>
			) : (
				<>
					<TextField label={a.note} value={note} onChange={setNote} maxLength={500} />
					<div className="grid grid-cols-2 gap-2">
						{(outcomes.data ?? []).map((outcome) => (
							<Button key={outcome.value} variant={outcome.value === "PRESENT" ? "primary" : "secondary"} isPending={record.isPending && record.variables === outcome.value} onPress={() => record.mutate(outcome.value)}>
								{outcome.label}
							</Button>
						))}
					</div>
				</>
			)}
			<div className="flex flex-col gap-3 border-t border-separator pt-4">
				<h3 className="font-medium">{a.move}</h3>
				<p className="text-sm text-muted">{a.moveHint}</p>
				<DatePick label={a.moveTo} value={newDate} onChange={setNewDate} />
				<Button variant="secondary" isDisabled={!newDate} isPending={move.isPending} onPress={() => move.mutate()}>
					{a.moveGo}
				</Button>
			</div>
		</div>
	);
}
